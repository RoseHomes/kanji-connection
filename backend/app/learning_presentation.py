"""Objective learner presentations over authorized, reviewed content. No SQL writes."""

import hashlib
import re

from fastapi import HTTPException
from sqlalchemy import select

from .learning import Learning, public_lesson
from .models import LessonRecord, LessonSection, QuizQuestion
from .reading_variants import READING_VARIANTS
from .sample_repository import SampleRepository

VERSION = "mcq-2026-11-19-v1"


def identity(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def kana(value):
    return "".join(chr(ord(c) - 96) if "ァ" <= c <= "ヶ" else c for c in value).strip()


def reading_variants():
    return READING_VARIANTS


def tokens(value):
    return {re.sub(r"\s+", "", s) for s in re.split(r"[/;；()（）]", value) if s.strip()}


def overlaps(left, right):
    return any(a in b or b in a for a in tokens(left) for b in tokens(right))


def make_question(key, prompt, kind, correct, wrong, explanation, source_key):
    labels = [correct]
    for label in wrong:
        if label and label not in labels:
            labels.append(label)
        if len(labels) == 4:
            break
    if len(labels) < 3:
        raise ValueError("Insufficient distinct verified distractors")
    options = [{"id": "choice-" + identity(key + label), "text": label} for label in labels]
    correct_id = options[0]["id"]
    options.sort(key=lambda option: identity(key + option["id"]))
    return {
        "id": VERSION + "-" + identity(key),
        "prompt": prompt,
        "kind": kind,
        "options": options,
        "correct_option_id": correct_id,
        "explanation": explanation,
        "source_question_key": source_key,
        "presentation_version": VERSION,
    }


def objective_questions(cards, vocabulary, originals, rubric=None, *, slug):
    """All distractor labels come from reviewed records; valid reading variants excluded."""
    questions = []
    meanings = list(dict.fromkeys(c["meaning_th"] for c in cards if c.get("meaning_th")))
    readings = list(dict.fromkeys(w["reading"] for w in vocabulary))
    for i, original in enumerate(originals):
        key = f"{slug}:{original['key']}"
        if original["type"] == "kanji_meaning":
            card = next(c for c in cards if c["character"] == original["prompt"])
            answer = card["meaning_th"]
            wrong = [s for s in meanings if not overlaps(s, answer)]
            # A recognition variant uses the same reviewed meaning, never infers a new sense.
            ordinal = (
                int(original["key"].split("-")[-1]) - 1 if original["key"].startswith("q-") else i
            )
            if ordinal % 2 and len(cards) >= 4:
                distractors = [
                    c["character"]
                    for c in cards
                    if c["character"] not in {card["character"], "靖", "訊"}
                    and not overlaps(c["meaning_th"], answer)
                ]
                q = make_question(
                    key,
                    f"คันจิตัวใดตรงกับความหมาย “{answer}” ในบทนี้?",
                    "glyph",
                    card["character"],
                    distractors,
                    f"{card['character']} — {answer}. {card.get('memory_note', '')}",
                    original["key"],
                )
            else:
                q = make_question(
                    key,
                    f"「{card['character']}」มีความหมายใดตามที่เรียนในบทนี้?",
                    "meaning",
                    answer,
                    wrong,
                    f"{card['character']} — {answer}. {card.get('memory_note', '')}",
                    original["key"],
                )
        elif original["type"] == "vocabulary_reading":
            w = next(w for w in vocabulary if w["word"] == original["prompt"])
            accepted = {kana(s.strip()) for s in re.split(r"[/／;；]", original["answer"])}
            accepted |= {kana(s) for s in reading_variants().get(w["word"], [])}
            accepted.add(kana(w["reading"]))
            wrong = [s for s in readings if kana(s) not in accepted]
            wrong.sort(key=lambda s: abs(len(s) - len(w["reading"])))
            q = make_question(
                key,
                f"คำว่า「{w['word']}」({w['meaning_th']}) อ่านอย่างไร?",
                "reading",
                w["reading"],
                wrong,
                f"{w['word']} อ่านว่า {w['reading']} — {w['meaning_th']}. {w.get('usage_notes', '')}",
                original["key"],
            )
        else:
            continue
        questions.append(q)
    if rubric:
        a, b = rubric["targets"]
        model = rubric["model_response_th"]
        swap = model.replace(a, "\x01").replace(b, a).replace("\x01", b)
        questions.append(
            make_question(
                f"{slug}:objective-shape-v1",
                f"ข้อใดอธิบายจุดต่างของรูป「{a} / {b}」ได้ถูกต้อง?",
                "shape",
                model,
                [rubric["incorrect_response_th"], swap, "ทั้งสองตัวมีรูปเหมือนกันทุกส่วน ต่างกันเพียงคำอ่าน"],
                model + ". จุดสังเกต: " + rubric["accepted_feature_th"],
                "comparison-c",
            )
        )
    return questions


def authorized_material(db, settings, user, slug):
    if db is None:
        lesson = SampleRepository().lesson(slug)
        cards = [
            {"character": c.character, "meaning_th": c.meaning_th, "memory_note": c.note_th}
            for c in lesson.kanjis
        ]
        vocabulary = [
            {"word": c.character, "reading": c.kunyomi[0], "meaning_th": c.meaning_th}
            for c in lesson.kanjis
        ]
        originals = [
            {
                "key": f"sample-{c.character}",
                "type": "vocabulary_reading",
                "prompt": c.character,
                "answer": c.kunyomi[0],
            }
            for c in lesson.kanjis
        ]
        return cards, vocabulary, originals, None
    service = Learning(db, settings, user)
    lesson = service.lesson(slug)  # Authorization always precedes presentation/cache access.
    visible = ["published", "sample"] if settings.expose_samples else ["published"]
    sections = select(LessonSection).where(LessonSection.lesson_id == lesson.id)
    if not service.private:
        sections = sections.where(
            LessonSection.access_tier == "free", LessonSection.status.in_(visible)
        )
    cards, vocabulary, rubric = [], [], None
    for section in db.scalars(sections.order_by(LessonSection.position)):
        for block in section.blocks:
            if block.get("kind") == "source_page_text":
                continue
            cards.extend(block.get("cards", []))
            vocabulary.extend(block.get("vocabulary", []))
            rubric = block.get("comparison_rubric") or rubric
    query = select(QuizQuestion).where(QuizQuestion.lesson_id == lesson.id)
    if not service.private:
        query = query.where(QuizQuestion.status.in_(visible))
    originals = [
        {
            "key": q.stable_key,
            "type": q.question_type,
            "prompt": q.prompt["text"],
            "answer": q.answer_key.get("text", ""),
        }
        for q in db.scalars(query.order_by(QuizQuestion.stable_key))
    ]
    # A published section must not promote a source question still under review.
    if not any(q["key"] == "comparison-c" for q in originals):
        rubric = None
    return cards, vocabulary, originals, rubric


def practice(db, settings, user, slug):
    cards, vocabulary, originals, rubric = authorized_material(db, settings, user, slug)
    if not cards or not originals:
        return []
    return objective_questions(cards, vocabulary, originals, rubric, slug=slug)


def practice_feedback(question):
    correct = next(o for o in question["options"] if o["id"] == question["correct_option_id"])
    return {
        "correct_option_id": correct["id"],
        "correct_text": correct["text"],
        "explanation": question["explanation"],
        "selection_explanations": {
            "correct": "เลือกได้ตรงกับสิ่งที่เรียนแล้ว",
            "incorrect": "ตัวเลือกนี้ไม่ตรงกับคำหรือจุดต่างที่โจทย์ถาม",
        },
    }


def public_question(question, *, include_feedback=False):
    public = {k: question[k] for k in ["id", "prompt", "kind", "options"]}
    if include_feedback:
        public["feedback"] = practice_feedback(question)
    return public


def check_choice(db, settings, user, slug, question_id, choice_id, *, submission_id=None):
    question = next((q for q in practice(db, settings, user, slug) if q["id"] == question_id), None)
    if question is None:
        raise HTTPException(404, "Question unavailable")
    selected = next((o for o in question["options"] if o["id"] == choice_id), None)
    if selected is None:
        raise HTTPException(422, "Choose one of the provided options")
    feedback = practice_feedback(question)
    explanations = feedback.pop("selection_explanations")
    correct = choice_id == feedback["correct_option_id"]
    result = {
        **feedback,
        "correct": correct,
        "selection_explanation": explanations["correct" if correct else "incorrect"],
        "persisted": False,
    }
    if submission_id is not None:
        service = Learning(db, settings, user)
        source = service.question(f"{slug}:{question['source_question_key']}")
        return service.record_attempt(
            source,
            submission_id,
            choice_id,
            {**result, "persisted": True, "status": "graded"},
            presentation=question_id,
        )
    return result


def comparison_groups(db, settings, user):
    if db is None:
        cards = SampleRepository().lesson("chapter-02").kanjis
        return [
            {
                "id": "sample-wood",
                "title": "จากต้นไม้สู่ป่า",
                "chapter": 2,
                "slug": "chapter-02",
                "category": "ส่วนประกอบ",
                "difference_th": "木 หนึ่งต้น; 林 มี 木 สองตัว; 森 มี 木 สามตัว",
                "characters": [
                    {
                        "character": c.character,
                        "meaning_th": c.meaning_th,
                        "memory_note": c.note_th,
                        "reading": {
                            "form": c.character,
                            "reading": c.kunyomi[0],
                            "label_th": "คำอ่านตัวอย่าง",
                        },
                        "example": None,
                    }
                    for c in cards
                ],
            }
        ]
    service = Learning(db, settings, user)
    lessons = list(db.scalars(select(LessonRecord).order_by(LessonRecord.chapter)))
    lessons = [
        l
        for l in lessons
        if service.private or (public_lesson(l, settings.expose_samples) and l.catalog_visible)
    ]
    allowed = {l.id: l for l in lessons}
    query = select(LessonSection).where(LessonSection.lesson_id.in_(allowed))
    if not service.private:
        query = query.where(
            LessonSection.access_tier == "free",
            LessonSection.status.in_(
                ["published", "sample"] if settings.expose_samples else ["published"]
            ),
        )
    material = {i: {"cards": {}, "pairs": [], "rubric": None, "tips": []} for i in allowed}
    for section in db.scalars(query.order_by(LessonSection.position)):
        m = material[section.lesson_id]
        for block in section.blocks:
            for c in block.get("cards", []):
                m["cards"][c["character"]] = c
            m["pairs"].extend(block.get("pairs", []))
            m["tips"].extend(block.get("memory_tips", []))
            m["rubric"] = block.get("comparison_rubric") or m["rubric"]
    groups = []
    for lid, m in material.items():
        lesson = allowed[lid]
        sets = [[s["kanji"] for s in pair] for pair in m["pairs"]]
        if lesson.chapter in [1, 17] and all(g in m["cards"] for g in ["休", "体"]):
            sets.append(["休", "体"])
        if lesson.chapter in [1, 12] and all(g in m["cards"] for g in ["大", "犬", "太"]):
            sets.insert(0, ["大", "犬", "太"])
        for i, glyphs in enumerate(sets):
            cards = []
            for g in glyphs:
                c = m["cards"].get(g)
                if c is None:
                    endpoint = next(s for p in m["pairs"] for s in p if s["kanji"] == g)
                    c = {
                        "character": g,
                        "meaning_th": endpoint["meaning_th"],
                        "memory_note": "ชื่อส่วนประกอบที่ใช้เปรียบเทียบรูป",
                        "reading_example": endpoint["reading"],
                        "study": {
                            "reading": {
                                "kind": "component",
                                "form": "",
                                "reading": endpoint["reading"],
                                "label_th": "ชื่อส่วนประกอบ",
                            }
                        },
                    }
                study = c.get("study", {})
                cards.append(
                    {
                        "character": g,
                        "meaning_th": c["meaning_th"],
                        "memory_note": c.get("memory_note", ""),
                        "reading": study.get(
                            "reading",
                            {
                                "form": g,
                                "reading": c["reading_example"],
                                "label_th": "คำอ่านตัวอย่างในบท",
                            },
                        ),
                        "example": {
                            k: v
                            for k, v in (study.get("example") or {}).items()
                            if k in {"word", "reading", "meaning_th", "optional", "target_scope"}
                        }
                        or None,
                    }
                )
            rubric = m["rubric"]
            relevant_tips = [t for t in m["tips"] if sum(g in t for g in glyphs) >= 2]
            difference = (
                rubric["model_response_th"]
                if rubric and set(glyphs) == set(rubric["targets"])
                else " · ".join(
                    relevant_tips or [f"{c['character']}: {c['memory_note']}" for c in cards]
                )
            )
            groups.append(
                {
                    "id": f"group-{lesson.chapter}-{i}",
                    "chapter": lesson.chapter,
                    "slug": lesson.slug,
                    "title": " / ".join(glyphs),
                    "category": "รูปพื้นฐาน"
                    if lesson.chapter <= 10
                    else "ตัวคล้ายกัน"
                    if lesson.chapter <= 15
                    else "ส่วนประกอบ"
                    if lesson.chapter <= 25
                    else "คันจิใช้งาน",
                    "difference_th": difference,
                    "characters": cards,
                }
            )
    return groups
