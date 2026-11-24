import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { m, AnimatePresence, useReducedMotion } from "motion/react";
import {
  ArrowRight,
  Check,
  CircleCheck,
  RotateCcw,
  Trophy,
  X,
} from "lucide-react";
import { api } from "../api";
import type { Health, Lesson, LessonDetail } from "../types";
import { useAuth } from "../auth";
import type { PracticeQuestion, ChoiceResult } from "../presentation-types";
import { DataState, EmptyState } from "../components";
import { PageHeading } from "../ui";
import { useReturnHref } from "../lesson-return";
import {
  queuePracticeSubmission,
  savePracticeSubmission,
  usePracticeSaves,
  type PracticeSubmission,
} from "../practice-saves";
import {
  AudioText,
  LessonAudioButton,
  useLessonAudioAvailable,
  useStopAudioOnChange,
} from "../lesson-audio";
type Attempt = {
  question: PracticeQuestion;
  choice: string;
  result: ChoiceResult;
  submissionId?: string;
};
const singleKanji = /^\p{Script=Han}$/u;
const japaneseScript =
  /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]/u;

function meaningGlyph(question: PracticeQuestion) {
  return question.kind === "meaning"
    ? question.prompt.match(/^「(\p{Script=Han})」/u)?.[1]
    : undefined;
}

function canHearMeaningPrompt(question: PracticeQuestion) {
  return (
    !!meaningGlyph(question) &&
    question.options.length > 0 &&
    question.options.every(
      ({ text }) =>
        /\p{Script=Thai}/u.test(text) &&
        !japaneseScript.test(text) &&
        !/[a-z]/i.test(text),
    )
  );
}

function QuizGlyphAudio({
  glyph,
  lesson,
  onlyCharacter = false,
  showText = false,
}: {
  glyph: string;
  lesson: LessonDetail | undefined;
  onlyCharacter?: boolean;
  showText?: boolean;
}) {
  if (!lesson || lesson.status !== "published" || lesson.private_development)
    return null;
  const lessonCards = lesson.sections?.flatMap((section) =>
    section.blocks.flatMap((block) => block.cards || []),
  );
  const reading = lessonCards?.find((card) => card.character === glyph)?.study
    ?.reading;
  if (!reading) return null;
  // After grading, a taught inflected form can play as a separately labelled word.
  if (
    !onlyCharacter &&
    reading.kind === "word" &&
    reading.form.includes(glyph)
  ) {
    return (
      <LessonAudioButton
        kind="word"
        text={reading.form}
        reading={reading.reading}
        slug={lesson.slug}
        quiz
        hideUnavailable
        showText
      />
    );
  }
  if (
    reading.form !== glyph ||
    (reading.kind !== "character" &&
      (onlyCharacter || reading.kind !== "component"))
  )
    return null;
  return (
    <LessonAudioButton
      kind={reading.kind === "component" ? "component" : "kanji"}
      text={glyph}
      reading={reading.reading}
      slug={lesson.slug}
      quiz
      hideUnavailable
      showText={showText}
    />
  );
}

function QuizAnswerAudio({
  question,
  result,
  slug,
  lesson,
  includeMeaning = false,
}: {
  question: PracticeQuestion;
  result: ChoiceResult;
  slug: string;
  lesson?: LessonDetail;
  includeMeaning?: boolean;
}) {
  if (question.kind !== "reading") {
    const glyphs =
      question.kind === "glyph"
        ? question.options.map(({ text }) => text)
        : question.kind === "shape"
          ? (question.prompt.match(/「([^」]+)」/)?.[1] || "").split(
              /\s*\/\s*/u,
            )
          : includeMeaning
            ? [meaningGlyph(question) || ""]
            : [];
    const forms = [
      ...new Set(glyphs.filter((glyph) => singleKanji.test(glyph))),
    ];
    if (!forms.length) return null;
    return (
      <div className="quiz-answer-audio" aria-label="ฟังคำอ่านหลังตรวจคำตอบ">
        {forms.map((glyph) => (
          <QuizGlyphAudio key={glyph} glyph={glyph} lesson={lesson} showText />
        ))}
      </div>
    );
  }
  const form = question.prompt.match(/「([^」]+)」/)?.[1];
  const correctReading = question.options.find(
    (option) => option.id === result.correct_option_id,
  )?.text;
  return (
    <div className="quiz-answer-audio" aria-label="ฟังคำอ่านหลังตรวจคำตอบ">
      {form && correctReading && (
        <span className="lesson-audio-line">
          <span lang="ja">{form}</span>
          <LessonAudioButton
            kind="word"
            text={form}
            reading={correctReading}
            slug={slug}
            quiz
          />
        </span>
      )}
      {question.options.map(({ id, text }) => (
        <span className="lesson-audio-line" key={id}>
          <span lang="ja">{text}</span>
          <LessonAudioButton
            kind="quiz_choice"
            text={text}
            reading={text}
            slug={slug}
            quiz
          />
        </span>
      ))}
    </div>
  );
}
export default function Quiz() {
  const { slug } = useParams();
  const catalog = useQuery({
    queryKey: ["learner-catalog"],
    queryFn: () => api<Lesson[]>("/learning/catalog"),
  });
  const questions = useQuery({
    queryKey: ["practice", slug],
    queryFn: () => api<PracticeQuestion[]>(`/learning/practice/${slug}?include_feedback=true`),
    enabled: !!slug,
  });
  const lesson = catalog.data?.find((l) => l.slug === slug);
  return (
    <div className="page section practice-page">
      <PageHeading
        eyebrow="LITTLE CHOICES. REAL UNDERSTANDING."
        title={slug ? "ลองเชื่อมความเข้าใจ" : "วันนี้ อยากฝึกเรื่องไหน"}
      >
        <p>{lesson?.title_th || "เลือกบท แล้วลองตอบจากสิ่งที่สังเกต ไม่ต้องพิมพ์คำตอบ"}</p>
      </PageHeading>
      <DataState
        loading={slug ? questions.isPending : catalog.isPending}
        error={slug ? questions.error : catalog.error}
        retry={() => {
          void questions.refetch();
          void catalog.refetch();
        }}
      />
      {!slug ? (
        <div className="lesson-grid">
          {catalog.data?.map((l) => (
            <Link
              className="lesson-card practice-chapter"
              key={l.slug}
              to={`/quiz/${l.slug}`}
            >
              <p className="eyebrow">
                ฝึกบทที่ {String(l.chapter).padStart(2, "0")}
              </p>
              <div className="chapter-glyphs" lang="ja">
                {l.anchors.slice(0, 3).join(" ")}
              </div>
              <h2>{l.title_th}</h2>
              <span className="text-link">
                เริ่มเลือกคำตอบ
                <ArrowRight size={18} />
              </span>
            </Link>
          ))}
          {catalog.data?.length === 0 && (
            <EmptyState title="แบบฝึกหัดกำลังเตรียมพร้อม">
              <Link to="/lessons">ดูบทเรียนที่พร้อมอ่าน</Link>
            </EmptyState>
          )}
        </div>
      ) : (
        questions.data && (
          <PracticeRound key={slug} questions={questions.data} slug={slug} />
        )
      )}
    </div>
  );
}
export function PracticeRound({
  questions,
  slug,
  variant = "quiz",
}: {
  questions: PracticeQuestion[];
  slug: string;
  variant?: "quiz" | "checkpoint";
}) {
  const { session, configured, ready } = useAuth();
  const cache = useQueryClient();
  const ownerId = session?.user.id;
  const accountQuiz = variant === "quiz" && !!ownerId;
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<Health>("/health", { anonymous: true }),
    enabled: accountQuiz,
  });
  const checkingSession = variant === "quiz" && configured && !ready;
  const accountUnavailable = checkingSession || (accountQuiz && !health.data);
  const savingOwner = accountQuiz && health.data?.account_writes_enabled ? ownerId : undefined;
  const pendingAttempt = useRef<PracticeSubmission | null>(null);
  const submitting = useRef(false);
  const lessonHref = useReturnHref(slug);
  const reduce = useReducedMotion();
  const [round, setRound] = useState(questions);
  const [index, setIndex] = useState(0);
  const [choice, setChoice] = useState("");
  const [history, setHistory] = useState<Attempt[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [review, setReview] = useState(false);
  const feedback = useRef<HTMLDivElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const question = round[index];
  const result = history[index]?.result;
  const onSaved = useCallback((id: string, saved: ChoiceResult) => {
    setHistory((attempts) => attempts.map((attempt) =>
      attempt.submissionId === id ? { ...attempt, result: saved } : attempt,
    ));
    void cache.invalidateQueries({ queryKey: ["dashboard", ownerId] });
  }, [cache, ownerId]);
  const saves = usePracticeSaves(savingOwner, onSaved);
  const saveStatus = (
    <>
      {saves.saving && <p className="subtle" role="status">กำลังบันทึกคำตอบในบัญชี…</p>}
      {saves.error && (
        <div className="notice" role="alert">
          <p>คำตอบยังอยู่ในเบราว์เซอร์และรอบันทึกในบัญชี · {saves.error}</p>
          <button onClick={() => void saves.retry()}>ลองบันทึกอีกครั้ง</button>
        </div>
      )}
    </>
  );
  const promptGlyph = question && meaningGlyph(question);
  const audioAvailable = useLessonAudioAvailable();
  const audioLesson = useQuery({
    queryKey: ["lesson", slug],
    queryFn: () => api<LessonDetail>(`/learning/lesson/${slug}`),
    enabled: audioAvailable && questions.some(({ kind }) => kind === "meaning" || kind === "glyph" || kind === "shape"),
    retry: false,
  });
  useStopAudioOnChange(`${slug}:${question?.id || "results"}:${review}`);
  useEffect(() => {
    const timer = window.setTimeout(
      () => heading.current?.focus({ preventScroll: true }),
      reduce ? 0 : 220,
    );
    return () => window.clearTimeout(timer);
  }, [index, round, reduce]);
  const check = async () => {
    if (!choice || submitting.current || result || !question || accountUnavailable) return;
    submitting.current = true;
    setError("");
    try {
      let localResult: ChoiceResult | undefined;
      if (question.feedback) {
        const { selection_explanations, ...key } = question.feedback;
        const correct = choice === key.correct_option_id;
        localResult = {
          ...key,
          correct,
          selection_explanation: selection_explanations[correct ? "correct" : "incorrect"],
          persisted: false,
        };
      }
      let r = localResult;
      let submissionId: string | undefined;
      let queued: PracticeSubmission | undefined;
      if (savingOwner) {
        if (
          pendingAttempt.current?.questionId !== question.id ||
          pendingAttempt.current.choice !== choice
        ) {
          pendingAttempt.current = {
            slug,
            questionId: question.id,
            choice,
            id: crypto.randomUUID(),
          };
        }
        const submission = pendingAttempt.current;
        submissionId = submission.id;
        if (localResult) {
          try {
            queuePracticeSubmission(savingOwner, submission);
            queued = submission;
          } catch {
            // Wait for server confirmation when browser storage is unavailable.
          }
        }
        if (!queued) {
          setBusy(true);
          r = await savePracticeSubmission(savingOwner, submission);
          onSaved(submission.id, r);
        }
        pendingAttempt.current = null;
      }
      if (!r) {
        setBusy(true);
        r = await api<ChoiceResult>(
          `/learning/practice/${slug}/${question.id}/check`,
          {
            method: "POST",
            body: JSON.stringify({ option_id: choice }),
          },
        );
      }
      const attempt = { question, choice, result: r, submissionId };
      setHistory((h) => [...h, attempt]);
      if (queued) void saves.send(queued);
      requestAnimationFrame(() =>
        feedback.current?.focus({ preventScroll: true }),
      );
    } catch (e) {
      submitting.current = false;
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const retry = (wrongOnly: boolean) => {
    const next = wrongOnly
      ? history.filter((a) => !a.result.correct).map((a) => a.question)
      : questions;
    submitting.current = false;
    setRound(next);
    setHistory([]);
    setIndex(0);
    setChoice("");
    setReview(false);
  };
  if (!questions.length)
    return (
      <EmptyState title="บทนี้ยังไม่มีชุดคำถามที่พร้อมเรียน">
        <p>กลับไปดูรูปและคำศัพท์ก่อน แล้วลองเลือกบทอื่นได้เสมอ</p>
        <Link className="button primary" to={lessonHref}>
          กลับบทเรียน
        </Link>
      </EmptyState>
    );
  if (!question) {
    const correct = history.filter((a) => a.result.correct).length;
    const pending = savingOwner && history.some((attempt) =>
      attempt.submissionId && !attempt.result.persisted,
    );
    return (
      <m.section
        className="results-panel"
        initial={{ opacity: 0, scale: reduce ? 1 : 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
      >
        <span className="completion-icon">
          <Trophy size={42} />
        </span>
        <p className="eyebrow">ANOTHER CONNECTION MADE</p>
        <h2 ref={heading} tabIndex={-1}>
          {variant === "checkpoint"
            ? "ลองเช็กแล้ว ไปเรียนต่อได้เลย"
            : "เก่งขึ้นอีกหนึ่งความเชื่อมโยง"}
        </h2>
        <div className="result-score">
          {correct}
          <span> / {history.length}</span>
        </div>
        <p>
          ตอบถูก {correct} ข้อ · ทบทวนอีกนิด {history.length - correct} ข้อ
        </p>
        <p className="subtle">
          {history.every((attempt) => attempt.result.persisted)
            ? "บันทึกคำตอบในประวัติบัญชีแล้ว"
            : pending
              ? "คำตอบที่ยังไม่ยืนยันอยู่ในคิวบันทึกของเบราว์เซอร์"
              : history.some((attempt) => attempt.result.persisted)
                ? "บันทึกคำตอบบางข้อในประวัติบัญชีแล้ว"
                : "ผลรอบนี้อยู่เฉพาะหน้านี้ ไม่ได้บันทึกในบัญชี"}
        </p>
        {saveStatus}
        <div className="hero-actions">
          {correct < history.length && (
            <button className="primary" onClick={() => retry(true)}>
              <RotateCcw size={17} />
              ลองข้อที่ยังสับสน
            </button>
          )}
          <button onClick={() => setReview(!review)} aria-expanded={review}>
            ดูคำตอบทั้งรอบ
          </button>
          <button onClick={() => retry(false)}>เริ่มรอบใหม่</button>
          {variant === "quiz" && (
            <Link className="button secondary" to={lessonHref}>
              กลับไปทบทวนบทเรียน
            </Link>
          )}
        </div>
        {review && (
          <ol className="answer-review">
            {history.map((a, i) => (
              <li key={a.question.id}>
                <strong>
                  {a.result.correct ? (
                    <CircleCheck size={18} />
                  ) : (
                    <RotateCcw size={18} />
                  )}{" "}
                  ข้อ {i + 1}: <AudioText text={a.question.prompt} slug={slug} quiz />
                </strong>
                <p>คำตอบที่ตรงกับโจทย์: <AudioText text={a.result.correct_text} slug={slug} quiz /></p>
                <p><AudioText text={a.result.explanation} slug={slug} quiz /></p>
                <QuizAnswerAudio question={a.question} result={a.result} slug={slug} lesson={audioLesson.data} includeMeaning />
              </li>
            ))}
          </ol>
        )}
      </m.section>
    );
  }
  return (
    <div className="quiz-shell">
      {checkingSession && <p role="status">กำลังตรวจบัญชี…</p>}
      {accountQuiz && !health.data && (
        <DataState
          loading={health.isPending}
          error={health.error}
          retry={() => void health.refetch()}
        />
      )}
      <div className="quiz-topline">
        {variant === "quiz" && <Link to={lessonHref}>← กลับบทเรียน</Link>}
        <span>
          ข้อ {index + 1} จาก {round.length}
        </span>
        <span>ถูกแล้ว {history.filter((a) => a.result.correct).length} ข้อ</span>
      </div>
      <div
        className="quiz-progress"
        role="progressbar"
        aria-label="ความคืบหน้าแบบฝึกหัด"
        aria-valuenow={index + (result ? 1 : 0)}
        aria-valuemin={0}
        aria-valuemax={round.length}
      >
        <m.span
          animate={{
            width: `${((index + (result ? 1 : 0)) / round.length) * 100}%`,
          }}
          transition={{ duration: reduce ? 0 : 0.2 }}
        />
      </div>
      <AnimatePresence mode="wait" initial={false}>
        <m.section
          key={question.id}
          className="question-panel"
          initial={{ opacity: 0, x: reduce ? 0 : 10 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduce ? 0 : 0.18 }}
        >
          <span className="question-kind">
            {{
              meaning: "เชื่อมรูปกับความหมาย",
              reading: "อ่านคำศัพท์ทั้งคำ",
              glyph: "เลือกตัวอักษร",
              shape: "สังเกตความต่าง",
            }[question.kind] || "ลองเลือกคำตอบ"}
          </span>
          <div className="quiz-prompt">
            <h2 ref={heading} tabIndex={-1}>{question.prompt}</h2>
            {promptGlyph && (result || canHearMeaningPrompt(question)) && (
              <QuizGlyphAudio glyph={promptGlyph} lesson={audioLesson.data} onlyCharacter={!result} />
            )}
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void check();
            }}
          >
            <fieldset className="mcq-options" disabled={busy || !!result}>
              <legend>เลือกคำตอบที่ตรงกับโจทย์</legend>
              {question.options.map((o, i) => (
                <label
                  className={`choice-card ${choice === o.id ? "chosen" : ""} ${result && o.id === result.correct_option_id ? "correct-choice" : ""} ${result && !result.correct && choice === o.id ? "incorrect-choice" : ""}`}
                  key={o.id}
                >
                  <input
                    type="radio"
                    name={question.id}
                    value={o.id}
                    checked={choice === o.id}
                    onChange={() => setChoice(o.id)}
                  />
                  <span className="choice-letter" aria-hidden="true">
                    {String.fromCharCode(65 + i)}
                  </span>
                  <span
                    className={
                      question.kind === "glyph" ? "choice-glyph" : "choice-text"
                    }
                    lang={
                      question.kind === "reading" || question.kind === "glyph"
                        ? "ja"
                        : "th"
                    }
                  >
                    {o.text}
                  </span>
                  {result && o.id === result.correct_option_id && (
                    <Check size={22} />
                  )}
                </label>
              ))}
            </fieldset>
            {!result && (
              <button
                className="primary check-answer"
                disabled={!choice || busy || accountUnavailable}
              >
                {busy ? "กำลังดูคำตอบ…" : "ตรวจคำตอบ"}
                <ArrowRight size={18} />
              </button>
            )}
          </form>
          {result && audioAvailable && (
            <QuizAnswerAudio question={question} result={result} slug={slug} lesson={audioLesson.data} />
          )}
          {error && (
            <p role="alert" className="notice">
              {error}
            </p>
          )}
          {result && (
            <m.div
              initial={{ opacity: 0, y: reduce ? 0 : 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`answer-feedback ${result.correct ? "is-correct" : "is-learning"}`}
              ref={feedback}
              tabIndex={-1}
              role="status"
              aria-live="polite"
            >
              <h3>
                {result.correct ? <CircleCheck size={24} /> : <X size={24} />}{" "}
                {result.correct
                  ? "ถูกต้อง เชื่อมโยงได้แล้ว!"
                  : "อีกนิดเดียว มาดูจุดสังเกตกัน"}
              </h3>
              <p><AudioText text={result.explanation} slug={slug} quiz /></p>
              {!result.correct && (
                <p>
                  <AudioText text={result.selection_explanation} slug={slug} quiz /> · คำตอบที่ตรงกับโจทย์:{" "}
                  {result.correct_text}
                </p>
              )}
              <button
                className="primary"
                onClick={() => {
                  submitting.current = false;
                  setIndex(index + 1);
                  setChoice("");
                }}
              >
                {index === round.length - 1 ? "ดูผลการฝึก" : "ข้อต่อไป"}
                <ArrowRight size={18} />
              </button>
            </m.div>
          )}
        </m.section>
      </AnimatePresence>
      {saveStatus}
      <p className="session-note">
        เลือกได้ทีละข้อ · ไม่ต้องพิมพ์ · {savingOwner ? "บันทึกคำตอบในบัญชีเบื้องหลัง" : "ฝึกครั้งนี้โดยไม่บันทึกผล"}
      </p>
    </div>
  );
}
