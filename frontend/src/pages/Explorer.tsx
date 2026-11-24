import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { KanjiReadingList } from "../lesson-audio";
import { Search, ArrowUpRight } from "lucide-react";
import { api } from "../api";
import type { Kanji, Lesson, LessonDetail } from "../types";
import { DataState, EmptyState } from "../components";
import { PageHeading, Chips } from "../ui";
import { learningGroups, chapterGroup } from "../presentation-types";
import { ChoicePicker } from "../selection-controls";
export default function Explorer() {
  const [category, setCategory] = useState("all");
  const [slug, setSlug] = useState("");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const catalog = useQuery({
    queryKey: ["learner-catalog"],
    queryFn: () => api<Lesson[]>("/learning/catalog"),
  });
  const chapters =
    catalog.data?.filter(
      (l) => category === "all" || chapterGroup(l.chapter || 2) === category,
    ) || [];
  const activeSlug =
    category === "all"
      ? slug
      : chapters.some((l) => l.slug === slug)
        ? slug
        : chapters[0]?.slug || "";
  const cards = useQuery({
    queryKey: ["explorer", q, offset],
    queryFn: () =>
      api<Kanji[]>(
        `/learning/kanjis?q=${encodeURIComponent(q)}&offset=${offset}&limit=31`,
      ),
    enabled: !activeSlug && category === "all",
  });
  const chapter = useQuery({
    queryKey: ["lesson", activeSlug],
    queryFn: () => api<LessonDetail>(`/learning/lesson/${activeSlug}`),
    enabled: !!activeSlug,
  });
  const scopedEmpty = category !== "all" && !chapters.length;
  const data = scopedEmpty
    ? []
    : activeSlug
      ? chapter.data?.kanjis
      : cards.data?.slice(0, 30);
  const loading = scopedEmpty
    ? catalog.isPending
    : activeSlug
      ? chapter.isPending
      : cards.isPending;
  return (
    <div className="page section">
      <PageHeading eyebrow="A WORLD OF CONNECTIONS" title="เริ่มรู้จัก ทีละตัว">
        <p>เลือกหมวดหรือบทที่สนใจ แล้วเปิดดูตัวอักษรที่อยากรู้จักเพิ่ม</p>
      </PageHeading>
      <Chips
        label="หมวดคันจิ"
        items={learningGroups}
        value={category}
        onChange={(v) => {
          setCategory(v);
          setSlug(
            v === "all"
              ? ""
              : catalog.data?.find((l) => chapterGroup(l.chapter || 2) === v)
                  ?.slug || "",
          );
          setQ("");
          setOffset(0);
        }}
      />
      <div className="explorer-toolbar">
        <ChoicePicker
          label="เลือกบทเรียนสำหรับสำรวจ"
          value={activeSlug || "all-chapters"}
          options={[
            ...(category === "all"
              ? [{ value: "all-chapters", label: "สำรวจตัวอักษรทั้งหมดที่พร้อมเรียน" }]
              : []),
            ...chapters.map((l) => ({
              value: l.slug,
              label: `บท ${l.chapter} · ${l.title_th}`,
            })),
          ]}
          onChange={(value) => {
            setSlug(value === "all-chapters" ? "" : value);
            setQ("");
            setOffset(0);
          }}
        />
        <label className="search-box">
          <Search size={19} />
          <span className="sr-only">ค้นหาเพิ่มเติม (ไม่จำเป็น)</span>
          <input
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setSlug("");
              setCategory("all");
              setOffset(0);
            }}
            placeholder="ค้นหาเพิ่มเติม เช่น ป่า หรือ 木"
            maxLength={100}
          />
        </label>
      </div>
      <DataState
        loading={loading}
        error={catalog.error || (activeSlug ? chapter.error : cards.error)}
        retry={() => {
          void cards.refetch();
          void chapter.refetch();
          void catalog.refetch();
        }}
      />
      <p className="count-label">
        {data?.length || 0} ตัวอักษรที่แสดง · เลือกเปิดดูคำศัพท์และภาพช่วยจำ
      </p>
      <div className="explorer-grid">
        {data?.map((k, i) => (
          <article
            className={`explorer-tile tone-${i % 4}`}
            key={k.character}
          >
            <Link className="explorer-tile-link" to={`/explore/${encodeURIComponent(k.character)}`}>
              <span className="explorer-glyph" lang="ja">{k.character}</span>
              <strong>{k.meaning_th}</strong>
              <ArrowUpRight size={18} aria-hidden="true" />
            </Link>
            <small>
              <KanjiReadingList character={k.character} readings={k.kunyomi.length ? k.kunyomi : k.onyomi} />
            </small>
          </article>
        ))}
      </div>
      {!loading && !data?.length && (
        <EmptyState title="ยังไม่พบตัวอักษรในชุดนี้">
          <p>ลองเลือกบทอื่นหรือล้างคำค้น ไม่ต้องพิมพ์ภาษาญี่ปุ่นก็สำรวจได้</p>
          <button
            onClick={() => {
              setQ("");
              setSlug("");
              setCategory("all");
            }}
          >
            ดูทั้งหมด
          </button>
        </EmptyState>
      )}
      {!activeSlug && !scopedEmpty && (
        <div className="hero-actions">
          <button
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - 30))}
          >
            ← ชุดก่อนหน้า
          </button>
          <button
            disabled={!cards.data || cards.data.length <= 30}
            onClick={() => setOffset(offset + 30)}
          >
            สำรวจชุดถัดไป →
          </button>
        </div>
      )}
    </div>
  );
}
