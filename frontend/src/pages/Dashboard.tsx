import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import { api } from "../api";
import { DataState, ReadOnlyNotice, AccountGate } from "../components";
import type { Health } from "../types";
import { guestSnapshot, readGuestLearning } from "../guest-learning";
import { readProgress } from "../progress";
import type { DashboardData, LearningLesson } from "../learning-types";

type Snapshot = ReturnType<typeof guestSnapshot>;
interface Preview {
  snapshot: string;
  rows: { key: string; kind: string; guest: object; cloud: object | null }[];
  unavailable: string[];
}
function questionLabel(key: string) {
  const chapter = key.match(/chapter-(\d+)/)?.[1];
  const number = key.match(/:q-(\d+)/)?.[1];
  return `บท ${Number(chapter) || "ตัวอย่าง"} · ${key.endsWith("comparison-c") ? "เปรียบเทียบ" : number ? `ข้อ ${Number(number)}` : "คำอ่านตัวอย่าง"}`;
}
function syncLabel(key: string) {
  if (key.startsWith("review:")) return `การ์ด ${key.slice(7)}`;
  if (key.startsWith("lesson:"))
    return `การอ่านบท ${Number(key.split("-").at(-1))}`;
  return "ประวัติคำตอบแบบฝึกหัด";
}
function syncValue(kind: string, value: object | null) {
  if (!value) return "ยังไม่มี";
  const data = value as Record<string, unknown>;
  if (kind === "lesson") return `อ่านแล้ว ${data.progress}%`;
  if (kind === "attempt")
    return data.already_imported
      ? "มีประวัตินี้ในบัญชีแล้ว"
      : questionLabel(String(data.question_key));
  const due =
    typeof data.due === "string"
      ? new Date(data.due).toLocaleDateString("th-TH")
      : "ไม่ระบุ";
  return `ทบทวน ${data.reviews} ครั้ง · จำไม่ได้ ${data.lapses ?? 0} ครั้ง · ช่วงห่าง ${data.interval ?? 1} วัน · กำหนด ${due}`;
}
export default function Dashboard() {
  const { session, ready } = useAuth();
  if (!ready)
    return (
      <div className="page section">
        <p role="status">กำลังตรวจบัญชี…</p>
      </div>
    );
  if (!session)
    return (
      <AccountGate
        title="พื้นที่การเรียนรู้ของคุณ"
        description="เข้าสู่ระบบเพื่อดูความก้าวหน้า ประวัติแบบฝึกหัด และคิวทบทวนส่วนตัว บทเรียนสาธารณะยังเปิดอ่านได้โดยไม่ต้องมีบัญชี"
      />
    );
  return <PersonalDashboard />;
}
function PersonalDashboard() {
  const { session, ready } = useAuth();
  const cache = useQueryClient();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<Health>("/health", { anonymous: true }),
    enabled: ready && !!session,
  });
  const readOnly = !!session && health.data?.account_writes_enabled !== true;
  const cloud = useQuery({
    queryKey: ["dashboard", session?.user.id],
    queryFn: () =>
      api<DashboardData>("/me/dashboard", { ownerId: session?.user.id }),
    enabled: ready && !!session,
  });
  const lessons = useQuery({
    queryKey: ["learning-lessons", session?.user.id],
    queryFn: () => api<LearningLesson[]>("/learning/lessons"),
    enabled: ready,
  });
  const [preview, setPreview] = useState<Preview | null>(null);
  const [captured, setCaptured] = useState<Snapshot | null>(null);
  const [choices, setChoices] = useState<Record<string, "guest" | "cloud">>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const local = readGuestLearning();
  const localCards = readProgress().cards;
  async function prepare() {
    if (readOnly) return;
    setBusy(true);
    setMessage("");
    setPreview(null);
    const guest = guestSnapshot();
    setCaptured(guest);
    try {
      const value = await api<Preview>("/me/sync/preview", {
        method: "POST",
        body: JSON.stringify(guest),
      });
      setPreview(value);
      // Existing records require an explicit radio choice; new records are proposed as imports.
      setChoices(
        Object.fromEntries(
          value.rows.filter((r) => !r.cloud).map((r) => [r.key, "guest"]),
        ),
      );
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function sync() {
    if (!preview || !captured || readOnly) return;
    setBusy(true);
    setMessage("");
    try {
      await api("/me/sync/apply", {
        ownerId: session?.user.id,
        method: "POST",
        body: JSON.stringify({
          guest: captured,
          snapshot: preview.snapshot,
          choices,
        }),
      });
      setPreview(null);
      setMessage("ซิงก์สำเร็จ · ยังคงเก็บสำเนาผู้เยี่ยมชมไว้ในเครื่อง");
      await cache.invalidateQueries({ queryKey: ["dashboard"] });
    } catch (e) {
      setMessage((e as Error).message);
      setPreview(null);
    } finally {
      setBusy(false);
    }
  }
  const records = cloud.data;
  const due =
    records?.due_count ??
    Object.values(localCards).filter((c) => Date.parse(c.due) <= Date.now())
      .length;
  const completed = records
    ? records.lessons.filter((l) => l.progress === 100).length
    : Object.values(local.lessons).filter((p) => p === 100).length;
  const correct =
    records?.quiz.correct ??
    local.attempts.filter((a) => a.result.correct === true).length;
  const graded =
    records?.quiz.graded ??
    local.attempts.filter((a) => a.result.status === "graded").length;
  return (
    <div className="page section personal-dashboard">
      <header>
        <p className="eyebrow">YOUR GROWING KNOWLEDGE</p>
        <h1>พื้นที่การเรียนรู้ของคุณ</h1>
        <p className="lead">
          {session ? "ความก้าวหน้าของบัญชีนี้" : "ผู้เยี่ยมชม · บันทึกเฉพาะเบราว์เซอร์เครื่องนี้"}
        </p>
      </header>
      {!session && (
        <Link className="button primary" to="/account">
          เข้าสู่ระบบเพื่อบันทึกข้ามอุปกรณ์
        </Link>
      )}
      {session && health.data && readOnly && <ReadOnlyNotice />}
      {session && (
        <DataState
          loading={cloud.isPending || health.isPending}
          error={cloud.error || health.error}
          retry={() => {
            void cloud.refetch();
            void health.refetch();
          }}
        />
      )}
      {(!session || records) && (
        <>
          <div className="stat-grid">
            <article className="notice">
              <strong>{completed}</strong>
              <p>บทที่อ่านจบ</p>
            </article>
            <article className="notice">
              <strong>
                {correct} / {graded}
              </strong>
              <p>คำตอบที่ตรวจแล้วและตอบถูก</p>
            </article>
            <article className="notice">
              <strong>{due}</strong>
              <p>การ์ดที่ถึงกำหนด</p>
            </article>
          </div>
          <div className="dashboard-actions">
            <Link className="button primary" to="/review">
              ทบทวนแฟลชการ์ด
            </Link>
            <Link className="button" to="/quiz">
              ทำแบบฝึกหัด
            </Link>
            <Link className="text-link" to="/account">
              จัดการบัญชี
            </Link>
          </div>
          {(records?.quiz.pending ??
            local.attempts.filter((a) => a.result.correct === null).length) >
            0 && <p className="notice">มีคำตอบแบบอธิบายที่ไม่รวมในคะแนนอัตโนมัติ</p>}
          <section
            className="dashboard-section"
            aria-labelledby="dashboard-progress"
          >
            <h2 id="dashboard-progress">ความก้าวหน้ารายบท</h2>
            {records?.lessons.length === 0 && (
              <p className="subtle">
                ยังไม่มีบทที่บันทึกความก้าวหน้า เลือกบทด้านล่างเพื่อเริ่มอ่าน
              </p>
            )}
            {records?.lessons.map((l) => (
              <article className="notice dashboard-progress-row" key={l.slug}>
                <Link to={`/lessons/${l.slug}`}>{l.title}</Link>
                <progress value={l.progress} max={100} aria-label={l.title} />
                <span>{l.progress}% · การอ่านที่บันทึกเอง</span>
              </article>
            ))}
          </section>
          {records && (
            <section
              className="dashboard-section"
              aria-labelledby="dashboard-results"
            >
              <h2 id="dashboard-results">ผลแบบฝึกหัดล่าสุด</h2>
              {records.quiz.recent.length === 0 && (
                <p className="subtle">ยังไม่มีคำตอบที่บันทึกในบัญชีนี้</p>
              )}
              {records.quiz.recent.length > 0 && (
                <ul className="history-list">
                  {records.quiz.recent.map((a, i) => (
                    <li key={`${a.question_key}:${i}`}>
                      <span>{questionLabel(a.question_key)}</span>
                      <span>
                        {a.correct === null
                          ? "ไม่คิดคะแนนอัตโนมัติ"
                          : a.correct
                            ? "ถูกต้อง"
                            : "ลองใหม่"}{" "}
                        · {new Date(a.created_at).toLocaleDateString("th-TH")}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}
        </>
      )}
      <section
        className="dashboard-section"
        aria-labelledby="dashboard-practice"
      >
        <h2 id="dashboard-practice">เลือกบทสำหรับฝึก</h2>
        {!session && (
          <p className="subtle">ประวัติแบบฝึกหัดในเครื่องเก็บล่าสุดไม่เกิน 200 ข้อ</p>
        )}
        <DataState
          loading={lessons.isPending}
          error={lessons.error}
          retry={() => void lessons.refetch()}
        />
        {!!lessons.data?.length && (
          <div className="lesson-grid">
            {lessons.data?.map((l) => (
              <Link className="notice" key={l.slug} to={`/quiz/${l.slug}`}>
                {l.title}
                {l.private_development && (
                  <small> · เนื้อหาส่วนตัวสำหรับทดสอบ</small>
                )}
              </Link>
            ))}
          </div>
        )}
        {lessons.data?.length === 0 && <p>ยังไม่มีบทที่เปิดให้ฝึกในบัญชีนี้</p>}
      </section>
      {session && (
        <section className="notice sync-panel">
          <h2>นำข้อมูลผู้เยี่ยมชมเข้าบัญชี</h2>
          <p>
            ตรวจข้อมูลก่อนส่ง และเลือกข้อมูลที่ต้องการเก็บเมื่อมีทั้งสองฝั่ง
            จะไม่รวมจำนวนหรือทับข้อมูลอัตโนมัติ สำเนาในเครื่องจะยังอยู่
          </p>
          <button onClick={() => void prepare()} disabled={busy || readOnly}>
            ตรวจข้อมูลก่อนซิงก์
          </button>
          {preview && (
            <>
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  setChoices({
                    ...choices,
                    ...Object.fromEntries(
                      preview.rows
                        .filter((row) => row.cloud)
                        .map((row) => [row.key, "cloud" as const]),
                    ),
                  })
                }
              >
                เก็บค่าบัญชีสำหรับรายการที่มีอยู่
              </button>
              <p>
                รายการพร้อมตรวจ {preview.rows.length} รายการ · ไม่พร้อมนำเข้า{" "}
                {preview.unavailable.length} รายการ
              </p>
              {preview.unavailable.length > 0 && (
                <p>
                  เก็บไว้ในเครื่อง: {preview.unavailable.map(syncLabel).join(", ")}
                </p>
              )}
              {preview.rows.map((row) => (
                <fieldset key={row.key}>
                  <legend>{syncLabel(row.key)}</legend>
                  <div className="sync-values">
                    <p>ในเครื่อง: {syncValue(row.kind, row.guest)}</p>
                    <p>บัญชี: {syncValue(row.kind, row.cloud)}</p>
                  </div>
                  <label>
                    <input
                      type="radio"
                      name={row.key}
                      checked={choices[row.key] === "guest"}
                      onChange={() =>
                        setChoices({ ...choices, [row.key]: "guest" })
                      }
                    />{" "}
                    ใช้ข้อมูลในเครื่อง
                    {row.kind === "attempt" && " (ตรวจคำตอบใหม่โดยเซิร์ฟเวอร์)"}
                  </label>
                  <label>
                    <input
                      type="radio"
                      name={row.key}
                      checked={choices[row.key] === "cloud"}
                      onChange={() =>
                        setChoices({ ...choices, [row.key]: "cloud" })
                      }
                    />{" "}
                    เก็บข้อมูลบัญชี
                  </label>
                </fieldset>
              ))}
              <button
                className="primary"
                disabled={
                  busy ||
                  readOnly ||
                  preview.rows.length === 0 ||
                  preview.rows.some((r) => !choices[r.key])
                }
                onClick={() => void sync()}
              >
                ยืนยันตัวเลือกและซิงก์
              </button>
              <button disabled={busy} onClick={() => setPreview(null)}>
                ยกเลิก
              </button>
            </>
          )}
        </section>
      )}
      {message && (
        <p className="notice" role="status">
          {message}
        </p>
      )}
    </div>
  );
}
