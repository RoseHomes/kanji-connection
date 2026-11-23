import { useEffect, useRef, useState } from "react";
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
import type { Health, Lesson } from "../types";
import { useAuth } from "../auth";
import type { PracticeQuestion, ChoiceResult } from "../presentation-types";
import { DataState, EmptyState } from "../components";
import { PageHeading } from "../ui";
import { useReturnHref } from "../lesson-return";
type Attempt = {
  question: PracticeQuestion;
  choice: string;
  result: ChoiceResult;
};
export default function Quiz() {
  const { slug } = useParams();
  const catalog = useQuery({
    queryKey: ["learner-catalog"],
    queryFn: () => api<Lesson[]>("/learning/catalog"),
  });
  const questions = useQuery({
    queryKey: ["practice", slug],
    queryFn: () => api<PracticeQuestion[]>(`/learning/practice/${slug}`),
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
              <div className="chapter-glyphs tone-2" lang="ja">
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
  const pendingAttempt = useRef<{
    question: string;
    choice: string;
    id: string;
  } | null>(null);
  const lessonHref = useReturnHref(slug);
  const reduce = useReducedMotion();
  const [round, setRound] = useState(questions);
  const [index, setIndex] = useState(0);
  const [choice, setChoice] = useState("");
  const [result, setResult] = useState<ChoiceResult | null>(null);
  const [history, setHistory] = useState<Attempt[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [review, setReview] = useState(false);
  const feedback = useRef<HTMLDivElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const question = round[index];
  useEffect(() => {
    const timer = window.setTimeout(
      () => heading.current?.focus({ preventScroll: true }),
      reduce ? 0 : 220,
    );
    return () => window.clearTimeout(timer);
  }, [index, round, reduce]);
  const check = async () => {
    if (!choice || busy || result || !question || accountUnavailable) return;
    setBusy(true);
    setError("");
    try {
      let r: ChoiceResult;
      if (accountQuiz && health.data?.account_writes_enabled) {
        if (
          pendingAttempt.current?.question !== question.id ||
          pendingAttempt.current.choice !== choice
        ) {
          pendingAttempt.current = {
            question: question.id,
            choice,
            id: crypto.randomUUID(),
          };
        }
        r = await api<ChoiceResult>(
          `/me/practice/${slug}/${question.id}/attempt`,
          {
            ownerId,
            method: "POST",
            body: JSON.stringify({
              option_id: choice,
              submission_id: pendingAttempt.current.id,
            }),
          },
        );
        pendingAttempt.current = null;
        void cache.invalidateQueries({ queryKey: ["dashboard", ownerId] });
      } else {
        r = await api<ChoiceResult>(
          `/learning/practice/${slug}/${question.id}/check`,
          {
            method: "POST",
            body: JSON.stringify({ option_id: choice }),
          },
        );
      }
      setResult(r);
      setHistory((h) => [...h, { question, choice, result: r }]);
      requestAnimationFrame(() =>
        feedback.current?.focus({ preventScroll: true }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const retry = (wrongOnly: boolean) => {
    const next = wrongOnly
      ? history.filter((a) => !a.result.correct).map((a) => a.question)
      : questions;
    setRound(next);
    setHistory([]);
    setIndex(0);
    setChoice("");
    setResult(null);
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
            : history.some((attempt) => attempt.result.persisted)
              ? "บันทึกคำตอบบางข้อในประวัติบัญชีแล้ว"
              : "ผลรอบนี้อยู่เฉพาะหน้านี้ ไม่ได้บันทึกในบัญชี"}
        </p>
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
                  ข้อ {i + 1}: {a.question.prompt}
                </strong>
                <p>คำตอบที่ตรงกับโจทย์: {a.result.correct_text}</p>
                <p>{a.result.explanation}</p>
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
          <h2 ref={heading} tabIndex={-1}>
            {question.prompt}
          </h2>
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
              <p>{result.explanation}</p>
              {!result.correct && (
                <p>
                  {result.selection_explanation} · คำตอบที่ตรงกับโจทย์:{" "}
                  {result.correct_text}
                </p>
              )}
              <button
                className="primary"
                onClick={() => {
                  setIndex((i) => i + 1);
                  setChoice("");
                  setResult(null);
                }}
              >
                {index === round.length - 1 ? "ดูผลการฝึก" : "ข้อต่อไป"}
                <ArrowRight size={18} />
              </button>
            </m.div>
          )}
        </m.section>
      </AnimatePresence>
      <p className="session-note">เลือกได้ทีละข้อ · ไม่ต้องพิมพ์ · ฝึกครั้งนี้โดยไม่บันทึกผล</p>
    </div>
  );
}
