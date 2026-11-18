import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../auth";
import { api } from "../api";
import {
  DataState,
  ReadOnlyNotice,
  PrivateNotice,
  EmptyState,
} from "../components";
import type { Health } from "../types";
import type { QuizResult } from "../guest-learning";
import type { LearningLesson, Question } from "../learning-types";
export default function Quiz() {
  const { slug } = useParams();
  const { session, ready } = useAuth();
  const cache = useQueryClient();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<Health>("/health", { anonymous: true }),
  });
  const lessons = useQuery({
    queryKey: ["learning-lessons", session?.user.id],
    queryFn: () =>
      api<LearningLesson[]>("/learning/lessons", { anonymous: !session }),
    enabled: ready || !session,
  });
  const questions = useQuery({
    queryKey: ["questions", slug, session?.user.id],
    queryFn: () =>
      api<Question[]>(`/learning/questions/${slug}`, { anonymous: !session }),
    enabled: (ready || !session) && !!slug,
  });
  if (!slug)
    return (
      <div className="page section">
        <p className="eyebrow">THE PRACTICE ROOM</p>
        <h1>ฝึกทีละความเชื่อมโยง</h1>
        <p className="lead">เลือกบท ลองตอบ และดูผลรอบนี้ · เริ่มได้โดยไม่ต้องมีบัญชี</p>
        <DataState
          loading={lessons.isPending}
          error={lessons.error}
          retry={() => void lessons.refetch()}
        />
        <div className="lesson-grid">
          {lessons.data?.map((l) => (
            <Link
              className="lesson-card available"
              to={`/quiz/${l.slug}`}
              key={l.slug}
            >
              <p className="eyebrow">PRACTICE</p>
              <h2>{l.title}</h2>
              <span className="text-link">เริ่มทำแบบฝึกหัด →</span>
              {l.private_development && " · ส่วนตัวสำหรับทดสอบ"}
            </Link>
          ))}
        </div>
        {lessons.data?.length === 0 && (
          <EmptyState title="แบบฝึกหัดสาธารณะกำลังเตรียมพร้อม">
            <p>คำถามจะแสดงเมื่อบทเรียนและแบบฝึกหัดได้รับอนุมัติเผยแพร่แล้ว</p>
            <Link className="text-link" to="/lessons">
              ดูบทเรียน
            </Link>
          </EmptyState>
        )}
      </div>
    );
  return (
    <div className="page section">
      <Link className="text-link" to="/quiz">
        ← เลือกบท
      </Link>
      <h1>
        แบบฝึกหัด ·{" "}
        {lessons.data?.find((l) => l.slug === slug)?.title ||
          "ฝึกทีละความเชื่อมโยง"}
      </h1>
      <p className="lead">
        {session &&
        health.data?.content_mode === "database" &&
        health.data.account_writes_enabled
          ? "บันทึกคำตอบกับบัญชี · เซิร์ฟเวอร์ตรวจคะแนน"
          : "ฝึกได้โดยไม่บันทึก · คำตอบและผลรอบนี้จะหายไปเมื่อออกจากหน้า"}
      </p>
      {lessons.data?.find((l) => l.slug === slug)?.private_development && (
        <PrivateNotice />
      )}
      <DataState
        loading={questions.isPending || health.isPending}
        error={questions.error || health.error}
        retry={() => {
          void questions.refetch();
          void health.refetch();
        }}
      />
      {session &&
        health.data?.content_mode === "database" &&
        !health.data.account_writes_enabled && <ReadOnlyNotice />}
      {questions.data && health.data && (
        <QuizRound
          key={`${slug}:${session?.user.id || "guest"}`}
          questions={questions.data}
          persist={
            !!session &&
            health.data.content_mode === "database" &&
            health.data.account_writes_enabled === true
          }
          readOnly={
            !!session &&
            health.data.content_mode === "database" &&
            !health.data.account_writes_enabled
          }
          privateDevelopment={
            lessons.data?.find((l) => l.slug === slug)?.private_development ===
            true
          }
          onSaved={() =>
            void cache.invalidateQueries({ queryKey: ["dashboard"] })
          }
        />
      )}
    </div>
  );
}
export function QuizRound({
  questions,
  persist,
  onSaved,
  readOnly = false,
  privateDevelopment = false,
}: {
  questions: Question[];
  persist: boolean;
  onSaved: () => void;
  readOnly?: boolean;
  privateDevelopment?: boolean;
}) {
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<QuizResult | null>(null);
  const [history, setHistory] = useState<QuizResult[]>([]);
  const [submission, setSubmission] = useState(() => crypto.randomUUID());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const question = questions[index];
  const canPersist = persist && !readOnly;
  async function check() {
    if (!question || busy || result) return;
    setBusy(true);
    setError("");
    try {
      const value = await api<QuizResult>(
        `${canPersist ? "/me/attempts/" : "/learning/check/"}${encodeURIComponent(question.key)}`,
        {
          method: "POST",
          anonymous: !canPersist && !privateDevelopment,
          body: JSON.stringify({ answer, submission_id: submission }),
        },
      );
      setResult(value);
      if (canPersist) onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!question)
    return (
      <div className="notice">
        <h2>
          {questions.length ? "ฝึกครบรอบแล้ว 🌱" : "บทนี้ยังไม่มีแบบฝึกหัดที่พร้อมให้ฝึก"}
        </h2>
        {questions.length > 0 && (
          <p>
            ตอบถูก {history.filter((r) => r.correct === true).length} จาก{" "}
            {history.filter((r) => r.status === "graded").length} ข้อที่ตรวจอัตโนมัติ
            · ไม่คิดคะแนน {history.filter((r) => r.correct === null).length} ข้อ
          </p>
        )}
        <div className="hero-actions">
          <Link className="button primary" to="/quiz">
            เลือกแบบฝึกหัดอื่น
          </Link>
          {canPersist ? (
            <Link className="text-link" to="/dashboard">
              ดูความก้าวหน้า
            </Link>
          ) : (
            <span className="subtle">ผลรอบนี้ไม่ได้บันทึกในบัญชีหรือเบราว์เซอร์</span>
          )}
        </div>
      </div>
    );
  return (
    <section className="notice quiz-panel">
      <progress
        aria-label="ความคืบหน้าแบบฝึกหัด"
        max={questions.length}
        value={index + (result ? 1 : 0)}
      />
      <p>
        ข้อ {index + 1} / {questions.length}
        {question.manual && " · ข้ออธิบาย ไม่มีคะแนนอัตโนมัติ"}
      </p>
      <h2 lang="ja">{question.prompt}</h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void check();
        }}
        className="learning-form"
      >
        <label>
          {question.manual ? "เขียนจุดที่ต่าง" : "คำตอบของคุณ"}
          <textarea
            lang={question.question_type.includes("reading") ? "ja" : "th"}
            rows={question.manual ? 4 : 2}
            maxLength={2000}
            value={answer}
            disabled={busy || !!result}
            onChange={(e) => setAnswer(e.target.value)}
          />
        </label>
        {question.options.length > 0 && (
          <fieldset className="answer-options">
            <legend>เลือกคำตอบ</legend>
            {question.options.map((o, i) => (
              <label key={i} className={answer === o.text ? "selected" : ""}>
                <input
                  type="radio"
                  name="answer-option"
                  checked={answer === o.text}
                  disabled={busy || !!result}
                  onChange={() => setAnswer(o.text)}
                />
                <span lang="ja">{o.text}</span>
              </label>
            ))}
          </fieldset>
        )}
        <button
          className="primary"
          disabled={busy || !!result || !answer.trim()}
        >
          {busy
            ? "กำลังตรวจคำตอบ…"
            : question.manual
              ? "ส่งคำอธิบาย"
              : "ตรวจคำตอบ"}
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
      {result && (
        <div role="status">
          <h3>
            {result.correct === null
              ? "ข้อนี้ไม่มีคะแนนอัตโนมัติ"
              : result.correct
                ? "ถูกต้อง ✓"
                : "ลองทบทวนอีกครั้ง"}
          </h3>
          {result.expected && (
            <p>
              คำตอบอ้างอิง: <span lang="ja">{result.expected}</span>
            </p>
          )}
          <p>{result.explanation}</p>
          <button
            onClick={() => {
              setHistory([...history, result]);
              setIndex(index + 1);
              setResult(null);
              setAnswer("");
              setSubmission(crypto.randomUUID());
            }}
          >
            ข้อถัดไป →
          </button>
        </div>
      )}
    </section>
  );
}
