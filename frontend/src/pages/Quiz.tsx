import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../auth";
import { api } from "../api";
import { DataState, ReadOnlyNotice, PrivateNotice } from "../components";
import type { Health } from "../types";
import { saveGuestAttempt, type QuizResult } from "../guest-learning";
import type { LearningLesson, Question } from "../learning-types";
export default function Quiz() {
  const { slug } = useParams();
  const { session, ready } = useAuth();
  const cache = useQueryClient();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<Health>("/health"),
  });
  const lessons = useQuery({
    queryKey: ["learning-lessons", session?.user.id],
    queryFn: () => api<LearningLesson[]>("/learning/lessons"),
    enabled: ready,
  });
  const questions = useQuery({
    queryKey: ["questions", slug, session?.user.id],
    queryFn: () => api<Question[]>(`/learning/questions/${slug}`),
    enabled: ready && !!slug,
  });
  if (!slug)
    return (
      <div className="page section">
        <h1>ฝึกทีละความเชื่อมโยง</h1>
        <DataState
          loading={lessons.isPending}
          error={lessons.error}
          retry={() => void lessons.refetch()}
        />
        <div className="lesson-grid">
          {lessons.data?.map((l) => (
            <Link className="notice" to={`/quiz/${l.slug}`} key={l.slug}>
              {l.title}
              {l.private_development && " · ส่วนตัวสำหรับทดสอบ"}
            </Link>
          ))}
        </div>
        {lessons.data?.length === 0 && (
          <p className="notice" role="status">
            ยังไม่มีแบบฝึกหัดที่เปิดให้บัญชีนี้เข้าถึง <Link to="/lessons">ดูบทเรียน</Link>
          </p>
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
        {session && health.data?.content_mode === "database"
          ? "บันทึกคำตอบกับบัญชี · เซิร์ฟเวอร์ตรวจคะแนน"
          : "ฝึกในเครื่อง · เก็บประวัติแบบผู้เยี่ยมชม"}
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
          persist={!!session && health.data.content_mode === "database"}
          readOnly={
            !!session &&
            health.data.content_mode === "database" &&
            !health.data.account_writes_enabled
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
}: {
  questions: Question[];
  persist: boolean;
  onSaved: () => void;
  readOnly?: boolean;
}) {
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<QuizResult | null>(null);
  const [history, setHistory] = useState<QuizResult[]>([]);
  const [submission, setSubmission] = useState(() => crypto.randomUUID());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const question = questions[index];
  async function check() {
    if (!question || busy || result || readOnly) return;
    setBusy(true);
    setError("");
    try {
      const value = await api<QuizResult>(
        `${persist ? "/me/attempts/" : "/learning/check/"}${encodeURIComponent(question.key)}`,
        {
          method: "POST",
          body: JSON.stringify({ answer, submission_id: submission }),
        },
      );
      if (
        !persist &&
        !saveGuestAttempt({
          answer,
          submission_id: submission,
          question_key: question.key,
          result: value,
        })
      )
        setError("แสดงผลได้ แต่บันทึกในเครื่องไม่สำเร็จ");
      setResult(value);
      onSaved();
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
            · รอตรวจ {history.filter((r) => r.correct === null).length} ข้อ
          </p>
        )}
        <Link className="button primary" to="/dashboard">
          ดูความก้าวหน้า
        </Link>
      </div>
    );
  return (
    <section className="notice quiz-panel">
      <p>
        ข้อ {index + 1} / {questions.length}
        {question.manual && " · เขียนอธิบาย แล้วรอตรวจ"}
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
        {question.options.map((o, i) => (
          <button
            type="button"
            key={i}
            disabled={busy || !!result}
            onClick={() => setAnswer(o.text)}
          >
            {o.text}
          </button>
        ))}
        <button
          className="primary"
          disabled={readOnly || busy || !!result || !answer.trim()}
        >
          {busy ? "กำลังบันทึก…" : question.manual ? "ส่งคำอธิบาย" : "ตรวจคำตอบ"}
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
      {result && (
        <div role="status">
          <h3>
            {result.correct === null
              ? "รอผู้สอนตรวจ · ยังไม่คิดคะแนน"
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
