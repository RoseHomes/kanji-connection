"""Learning transactions and owner-scoped operations. No schema or content writes."""

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select

from .catalog import SAMPLES
from .comparison_scoring import assess_comparison
from .models import KanjiRecord, LessonRecord, QuizAttempt, QuizQuestion, ReviewItem, UserProgress


def now():
    return datetime.now(timezone.utc)


def utc(value):
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def normalized(value):
    return unicodedata.normalize("NFC", value).strip()


def public_lesson(row, samples):
    return (row.status == "published" and row.access_tier == "free") or (
        samples and row.status == "sample" and row.access_tier == "free"
    )


class Learning:
    def __init__(self, session, settings, user=None):
        self.db, self.settings, self.user = session, settings, user
        self.private = (
            not settings.vercel and user is not None and user.id in settings.development_user_ids
        )

    def lesson(self, slug):
        row = self.db.scalar(select(LessonRecord).where(LessonRecord.slug == slug))
        if row is None or not (
            (public_lesson(row, self.settings.expose_samples) and row.catalog_visible)
            or self.private
        ):
            raise HTTPException(404, "Lesson unavailable")
        return row

    def kanji(self, char):
        row = self.db.scalar(select(KanjiRecord).where(KanjiRecord.character == char))
        if not self.can_see_kanji(row):
            raise HTTPException(404, "Card unavailable")
        return row

    def can_see_kanji(self, row):
        return row is not None and (
            (row.review_status == "published" and row.access_tier == "free")
            or (
                self.settings.expose_samples
                and row.review_status == "sample"
                and row.access_tier == "free"
            )
            or self.private
        )

    def question(self, key):
        try:
            slug, stable = key.split(":", 1)
        except ValueError:
            raise HTTPException(404, "Question unavailable") from None
        lesson = self.lesson(slug)
        row = self.db.scalar(
            select(QuizQuestion).where(
                QuizQuestion.lesson_id == lesson.id, QuizQuestion.stable_key == stable
            )
        )
        if row is None or not (
            row.status == "published"
            or (self.settings.expose_samples and row.status == "sample")
            or self.private
        ):
            raise HTTPException(404, "Question unavailable")
        return row

    def questions(self, slug):
        lesson = self.lesson(slug)
        visible = ["published", "sample"] if self.settings.expose_samples else ["published"]
        query = select(QuizQuestion).where(QuizQuestion.lesson_id == lesson.id)
        if not self.private:
            query = query.where(QuizQuestion.status.in_(visible))
        return [
            {
                "key": f"{slug}:{q.stable_key}",
                "prompt": q.prompt.get("text", ""),
                "question_type": q.question_type,
                "options": [
                    {"text": o} if isinstance(o, str) else {"text": o.get("text", "")}
                    for o in q.options
                ],
                "manual": q.answer_key.get("kind") == "reference_only",
            }
            for q in self.db.scalars(query.order_by(QuizQuestion.stable_key))
        ]

    def grade(self, question, answer):
        key = question.answer_key
        if key.get("kind") == "reference_only":
            rubric = key.get("rubric")
            assessment = (
                assess_comparison(answer, rubric)
                if rubric
                else {
                    "status": "needs_manual_review" if answer.strip() else "unanswered",
                    "score": None,
                }
            )
            return {
                "correct": None,
                "status": assessment["status"],
                "expected": None,
                "explanation": key.get("text", ""),
            }
        if key.get("kind") not in {"explicit_source", "sample"} or not isinstance(
            key.get("text"), str
        ):
            raise HTTPException(422, "Question has no supported scoring key")
        # No fuzzy matching or invented translation alternatives.
        alternatives = {normalized(key["text"])} | {
            normalized(part) for part in re.split(r"[/／;；]", key["text"]) if part.strip()
        }
        candidate = normalized(answer)
        if "reading" in question.question_type:

            def hiragana(value):
                return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in value)

            candidate = hiragana(candidate)
            alternatives = {hiragana(value) for value in alternatives}
        return {
            "correct": candidate in alternatives,
            "status": "graded",
            "expected": key["text"],
            "explanation": question.explanation_th,
        }

    def attempt(self, key, submission, answer):
        q = self.question(key)
        existing = self.db.scalar(
            select(QuizAttempt).where(
                QuizAttempt.owner_id == self.user.id, QuizAttempt.submission_id == submission
            )
        )
        result = self.grade(q, answer)
        if existing:
            if existing.question_id != q.id or existing.selected_answer.get("answer") != answer:
                raise HTTPException(409, "Submission identifier already used")
            # Replay stored outcome even if an editor subsequently changes an answer.
            return existing.selected_answer["result"]
        self.db.add(
            QuizAttempt(
                owner_id=self.user.id,
                submission_id=submission,
                question_id=q.id,
                selected_answer={
                    "answer": answer,
                    "grade_status": result["status"],
                    "result": result,
                },
                correct=result["correct"] is True,
                created_at=now(),
            )
        )
        self.db.flush()
        return result

    def progress(self, slug, amount, expected):
        lesson = self.lesson(slug)
        row = self.db.get(UserProgress, (self.user.id, lesson.id))
        if (row.version if row else 0) != expected:
            raise HTTPException(409, "Progress changed; refresh before saving")
        if row is None:
            row = UserProgress(owner_id=self.user.id, lesson_id=lesson.id, version=1)
            self.db.add(row)
        else:
            row.version += 1
        row.progress = amount
        row.updated_at = now()
        row.completed_at = now() if amount == 100 else None
        self.db.flush()
        return {"progress": row.progress, "version": row.version}

    def review_row(self, kanji_id):
        return self.db.scalar(
            select(ReviewItem).where(
                ReviewItem.owner_id == self.user.id, ReviewItem.kanji_id == kanji_id
            )
        )

    def review(self, char, knew, expected):
        kanji = self.kanji(char)
        row = self.review_row(kanji.id)
        if (row.version if row else 0) != expected:
            raise HTTPException(409, "Review changed; refresh before saving")
        if row is None:
            row = ReviewItem(
                owner_id=self.user.id,
                kanji_id=kanji.id,
                version=0,
                interval_days=0,
                reviews=0,
                lapses=0,
            )
            self.db.add(row)
        row.interval_days = min(90, max(1, row.interval_days * 2)) if knew else 1
        row.reviews += 1
        row.lapses += 0 if knew else 1
        row.due_at = now() + timedelta(days=row.interval_days)
        row.version += 1
        self.db.flush()
        return self.serialize_review(row)

    @staticmethod
    def serialize_review(row):
        return {
            "interval": row.interval_days,
            "due": utc(row.due_at).isoformat(),
            "reviews": row.reviews,
            "lapses": row.lapses,
            "version": row.version,
        }

    def dashboard(self):
        lesson_rows = []
        for p, lesson in self.db.execute(
            select(UserProgress, LessonRecord)
            .join(LessonRecord)
            .where(UserProgress.owner_id == self.user.id)
        ):
            if public_lesson(lesson, self.settings.expose_samples) or self.private:
                lesson_rows.append(
                    {
                        "slug": lesson.slug,
                        "title": lesson.title_th,
                        "progress": p.progress,
                        "version": p.version,
                    }
                )
        cards = {}
        for r, k in self.db.execute(
            select(ReviewItem, KanjiRecord)
            .join(KanjiRecord, KanjiRecord.id == ReviewItem.kanji_id)
            .where(ReviewItem.owner_id == self.user.id)
        ):
            if not self.can_see_kanji(k):
                continue
            cards[k.character] = self.serialize_review(r)
        attempts = []
        graded, correct, pending = 0, 0, 0
        # Filter ownership and content before aggregating. No user's private metadata is returned.
        for attempt, question, lesson in self.db.execute(
            select(QuizAttempt, QuizQuestion, LessonRecord)
            .join(QuizQuestion, QuizQuestion.id == QuizAttempt.question_id)
            .join(LessonRecord, LessonRecord.id == QuizQuestion.lesson_id)
            .where(QuizAttempt.owner_id == self.user.id)
            .order_by(QuizAttempt.created_at.desc())
        ):
            allowed = (
                public_lesson(lesson, self.settings.expose_samples)
                and (
                    question.status == "published"
                    or (self.settings.expose_samples and question.status == "sample")
                )
            ) or self.private
            if not allowed:
                continue
            status = attempt.selected_answer.get("grade_status", "graded")
            is_graded = status == "graded"
            graded += int(is_graded)
            correct += int(is_graded and attempt.correct)
            pending += int(not is_graded)
            if len(attempts) < 30:
                attempts.append(
                    {
                        "question_key": f"{lesson.slug}:{question.stable_key}",
                        "correct": attempt.correct if is_graded else None,
                        "status": status,
                        "created_at": utc(attempt.created_at).isoformat(),
                    }
                )
        return {
            "lessons": lesson_rows,
            "cards": cards,
            "quiz": {"graded": graded, "correct": correct, "pending": pending, "recent": attempts},
            "due_count": sum(
                utc(datetime.fromisoformat(r["due"])) <= now() for r in cards.values()
            ),
        }

    def preview_sync(self, guest):
        rows = []
        unavailable = []
        for char, record in guest.cards.items():
            if record.due > now() + timedelta(days=90, minutes=1):
                raise HTTPException(422, "Guest due date exceeds scheduling bounds")
            try:
                kanji = self.kanji(char)
            except HTTPException:
                unavailable.append(f"review:{char}")
                continue
            cloud = self.review_row(kanji.id)
            rows.append(
                {
                    "key": f"review:{char}",
                    "kind": "review",
                    "guest": record.model_dump(mode="json"),
                    "cloud": self.serialize_review(cloud) if cloud else None,
                }
            )
        for slug, value in guest.lessons.items():
            try:
                lesson = self.lesson(slug)
            except HTTPException:
                unavailable.append(f"lesson:{slug}")
                continue
            cloud = self.db.get(UserProgress, (self.user.id, lesson.id))
            rows.append(
                {
                    "key": f"lesson:{slug}",
                    "kind": "lesson",
                    "guest": {"progress": value},
                    "cloud": {"progress": cloud.progress, "version": cloud.version}
                    if cloud
                    else None,
                }
            )
        for a in guest.attempts:
            try:
                question = self.question(a.question_key)
            except HTTPException:
                unavailable.append(f"attempt:{a.submission_id}")
                continue
            existing = self.db.scalar(
                select(QuizAttempt).where(
                    QuizAttempt.owner_id == self.user.id,
                    QuizAttempt.submission_id == a.submission_id,
                )
            )
            if existing and (
                existing.question_id != question.id
                or existing.selected_answer.get("answer") != a.answer
            ):
                raise HTTPException(409, "Guest attempt identifier conflicts with cloud history")
            rows.append(
                {
                    "key": f"attempt:{a.submission_id}",
                    "kind": "attempt",
                    "guest": {"question_key": a.question_key},
                    "cloud": {"already_imported": True} if existing else None,
                }
            )
        token = hashlib.sha256(
            json.dumps(
                {"owner": str(self.user.id), "guest": guest.model_dump(mode="json"), "rows": rows},
                sort_keys=True,
            ).encode()
        ).hexdigest()
        return {"snapshot": token, "rows": rows, "unavailable": unavailable}

    def apply_sync(self, request):
        preview = self.preview_sync(request.guest)
        if request.snapshot != preview["snapshot"]:
            raise HTTPException(409, "Cloud progress changed; preview again")
        if set(request.choices) != {r["key"] for r in preview["rows"]}:
            raise HTTPException(422, "Choose guest or cloud for every available record")
        for row in preview["rows"]:
            key = row["key"]
            if request.choices[key] != "guest":
                continue
            identifier = key.split(":", 1)[1]
            if row["kind"] == "review":
                k = self.kanji(identifier)
                cloud = self.review_row(k.id)
                if cloud is None:
                    cloud = ReviewItem(owner_id=self.user.id, kanji_id=k.id, version=0)
                    self.db.add(cloud)
                guest = request.guest.cards[identifier]
                cloud.interval_days, cloud.due_at = guest.interval, guest.due
                cloud.reviews, cloud.lapses = guest.reviews, guest.lapses
                cloud.version += 1
            elif row["kind"] == "lesson":
                self.progress(
                    identifier,
                    request.guest.lessons[identifier],
                    row["cloud"]["version"] if row["cloud"] else 0,
                )
            else:
                attempt = next(
                    a for a in request.guest.attempts if str(a.submission_id) == identifier
                )
                self.attempt(attempt.question_key, attempt.submission_id, attempt.answer)
        self.db.flush()
        return {"synced": True, "unavailable": preview["unavailable"]}


def sample_questions():
    return [
        {
            "key": f"chapter-02:sample-{k.character}",
            "prompt": f"{k.character} — คำอ่านคุนโยมิ",
            "question_type": "kanji_reading",
            "options": [],
            "manual": False,
        }
        for k in SAMPLES
    ]


def grade_sample(key, answer):
    item = next((k for k in SAMPLES if key == f"chapter-02:sample-{k.character}"), None)
    if item is None:
        raise HTTPException(404, "Question unavailable")
    return {
        "correct": normalized(answer).translate(
            str.maketrans({chr(i): chr(i - 0x60) for i in range(0x30A1, 0x30F7)})
        )
        == item.kunyomi[0],
        "status": "graded",
        "expected": item.kunyomi[0],
        "explanation": "Independent sample reading checked against the cited KanjiPedia entry.",
        "persisted": False,
    }
