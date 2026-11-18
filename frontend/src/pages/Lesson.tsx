import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../auth";
import { saveGuestLesson } from "../guest-learning";
import type { DashboardData } from "../learning-types";
import { api } from "../api";
import type { Health, LessonDetail } from "../types";
import {
  DataState,
  KanjiCard,
  MemoryIllustration,
  ReadOnlyNotice,
} from "../components";
import { LessonSections } from "../lesson-sections";
export default function Lesson() {
  const { slug } = useParams();
  const { session, ready } = useAuth();
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<Health>("/health"),
  });
  const cloud = !!session && health.data?.content_mode === "database";
  const readOnly = cloud && health.data?.account_writes_enabled !== true;
  const progress = useQuery({
    queryKey: ["dashboard", session?.user.id],
    queryFn: () => api<DashboardData>("/me/dashboard"),
    enabled: cloud,
  });
  async function markRead() {
    if (!slug || readOnly || !health.data) return;
    setSaving(true);
    setMessage("");
    try {
      if (cloud) {
        await api(`/me/progress/${slug}`, {
          method: "PUT",
          body: JSON.stringify({
            progress: 100,
            expected_version:
              progress.data?.lessons.find((l) => l.slug === slug)?.version || 0,
          }),
        });
        await progress.refetch();
      } else if (!saveGuestLesson(slug)) throw new Error("บันทึกในเครื่องไม่สำเร็จ");
      setMessage("บันทึกว่าอ่านจบแล้ว · แยกจากคะแนนแบบฝึกหัด");
    } catch (e) {
      setMessage((e as Error).message);
      if (cloud) void progress.refetch();
    } finally {
      setSaving(false);
    }
  }
  const { data, isPending, error, refetch } = useQuery({
    queryKey: ["lesson", slug, session?.user.id],
    queryFn: () => api<LessonDetail>(`/learning/lesson/${slug}`),
    enabled: ready,
  });
  return (
    <div className="page section">
      <Link className="text-link" to="/lessons">
        ← บทเรียนทั้งหมด
      </Link>
      <DataState
        loading={isPending}
        error={error || health.error || progress.error}
        retry={() => {
          void refetch();
          void health.refetch();
          if (cloud) void progress.refetch();
        }}
      />
      {data && (
        <>
          <p className="eyebrow">
            CHAPTER {String(data.chapter ?? data.id).padStart(2, "0")}{" "}
            {data.status === "sample" ? "· บทเรียนตัวอย่าง" : ""}
          </p>
          <h1>{data.title_th}</h1>
          {data.private_development && (
            <p className="notice">ส่วนตัวสำหรับทดสอบ · เนื้อหายังไม่เผยแพร่</p>
          )}
          {readOnly && <ReadOnlyNotice />}
          <p className="lead">{data.introduction_th}</p>
          {data.status === "sample" && data.chapter === 2 && (
            <div className="lesson-banner">
              <MemoryIllustration count={3} />
              <div>
                <p className="eyebrow">สังเกต → แยกส่วน → เชื่อมโยง</p>
                <div className="glyph-sequence" lang="ja">
                  木 → 林 → 森
                </div>
                <p>ส่วนประกอบเดียวกัน ปรากฏในตำแหน่งและจำนวนที่ต่างกัน</p>
              </div>
            </div>
          )}
          {!!data.sections?.length && (
            <LessonSections
              sections={data.sections}
              kanjis={data.kanjis}
              slug={data.slug}
            />
          )}
          {!data.sections?.some((s) => s.kind === "cards") && (
            <div className="kanji-grid">
              {data.kanjis.map((k) => (
                <KanjiCard key={k.character} item={k} />
              ))}
            </div>
          )}
          <aside className="notice">
            <strong>แหล่งที่มาและสถานะเนื้อหา</strong>
            <p>{data.provenance}</p>
            {data.status === "sample" && data.chapter === 2 && (
              <p>本・末・未 และหัวข้ออื่นของบทนี้ยังไม่พร้อมเผยแพร่</p>
            )}
          </aside>
          <div className="hero-actions">
            <button
              disabled={
                saving || readOnly || !health.data || (cloud && !progress.data)
              }
              onClick={() => void markRead()}
            >
              บันทึกว่าอ่านจบแล้ว
            </button>
            <Link className="button" to={`/quiz/${data.slug}`}>
              ทำแบบฝึกหัด
            </Link>
            <Link className="button primary" to="/review">
              ฝึกด้วยแฟลชการ์ด <ArrowRight size={17} />
            </Link>
            <Link className="text-link" to="/compare">
              เปรียบเทียบตัวอักษร <ArrowRight size={17} />
            </Link>
          </div>
          {message && (
            <p className="notice" role="status">
              {message}
            </p>
          )}
        </>
      )}
    </div>
  );
}
