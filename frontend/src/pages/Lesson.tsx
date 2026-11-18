import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../auth";
import type { DashboardData } from "../learning-types";
import { api } from "../api";
import type { Health, LessonDetail, Lesson as LessonMetadata } from "../types";
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
    queryFn: () => api<Health>("/health", { anonymous: true }),
  });
  const cloud = !!session && health.data?.content_mode === "database";
  const readOnly = cloud && health.data?.account_writes_enabled !== true;
  const progress = useQuery({
    queryKey: ["dashboard", session?.user.id],
    queryFn: () => api<DashboardData>("/me/dashboard"),
    enabled: cloud,
  });
  async function markRead() {
    if (!slug || !session || !cloud || readOnly || !health.data) return;
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
      }
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
    queryFn: () =>
      api<LessonDetail>(`/learning/lesson/${slug}`, { anonymous: !session }),
    enabled: ready || !session,
  });
  const navigation = useQuery({
    queryKey: ["lesson-navigation", session?.user.id],
    queryFn: () =>
      api<LessonMetadata[]>("/learning/catalog", { anonymous: !session }),
    enabled: !!data,
  });
  const position =
    navigation.data?.findIndex((item) => item.slug === slug) ?? -1;
  const previous = position > 0 ? navigation.data?.[position - 1] : undefined;
  const next = position >= 0 ? navigation.data?.[position + 1] : undefined;
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
          <div className="study-toolbar">
            <span>{data.kanjis.length} ตัวอักษรในบทนี้</span>
            <a href="#lesson-content">เริ่มอ่านเนื้อหา ↓</a>
            <Link to={`/quiz/${data.slug}`}>ไปแบบฝึกหัด →</Link>
          </div>
          <div id="lesson-content" />
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
            {session ? (
              <button
                disabled={
                  saving ||
                  !cloud ||
                  readOnly ||
                  !health.data ||
                  (cloud && !progress.data)
                }
                onClick={() => void markRead()}
              >
                บันทึกว่าอ่านจบแล้ว
              </button>
            ) : (
              <Link className="button" to="/account">
                เข้าสู่ระบบเพื่อบันทึกความก้าวหน้า
              </Link>
            )}
            <Link className="button primary" to={`/quiz/${data.slug}`}>
              ทำแบบฝึกหัด
            </Link>
            <Link className="button" to="/review">
              แฟลชการ์ดส่วนตัว <ArrowRight size={17} />
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
          <nav className="lesson-navigation" aria-label="บทเรียนก่อนหน้าและถัดไป">
            {previous ? (
              <Link to={`/lessons/${previous.slug}`}>
                <small>← บทก่อนหน้า</small>
                {previous.title_th}
              </Link>
            ) : (
              <span />
            )}
            {next && (
              <Link to={`/lessons/${next.slug}`}>
                <small>บทถัดไป →</small>
                {next.title_th}
              </Link>
            )}
          </nav>
        </>
      )}
    </div>
  );
}
