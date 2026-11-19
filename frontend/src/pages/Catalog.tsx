import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowUpRight, BookOpen } from "lucide-react";
import { api } from "../api";
import type { Lesson } from "../types";
import { chapterGroup, learningGroups } from "../presentation-types";
import { DataState, EmptyState } from "../components";
import { Chips, PageHeading, Reveal } from "../ui";
export const parts = [
  "ทั้งหมด",
  "หมวด 1",
  "หมวด 2",
  "หมวด 3",
  "หมวด 4",
  "หมวด 5",
  "หมวด 6",
];
export default function Catalog() {
  const [params, setParams] = useSearchParams();
  const category = params.get("category") || "all";
  const lessons = useQuery({
    queryKey: ["learner-catalog"],
    queryFn: () => api<Lesson[]>("/learning/catalog"),
  });
  const visible =
    lessons.data?.filter(
      (l) => category === "all" || chapterGroup(l.chapter || 2) === category,
    ) || [];
  return (
    <div className="page section">
      <PageHeading eyebrow="THE LEARNING PATH" title="ทุกบท เชื่อมความเข้าใจ">
        <p>จากรูปที่คุ้นตา สู่คำที่ใช้ได้จริง เลือกจุดเริ่มต้นที่อยากรู้จัก</p>
      </PageHeading>
      <div className="catalog-toolbar">
        <Chips
          label="เลือกกลุ่มบทเรียน"
          items={learningGroups}
          value={category}
          onChange={(v) => setParams(v === "all" ? {} : { category: v })}
        />
        <span className="count-label">{visible.length} บทพร้อมอ่าน</span>
      </div>
      <DataState
        loading={lessons.isPending}
        error={lessons.error}
        retry={() => void lessons.refetch()}
      />
      {!lessons.isPending && !visible.length && (
        <EmptyState
          title={
            lessons.data?.length
              ? "ยังไม่มีบทในกลุ่มนี้"
              : "บทเรียนสาธารณะกำลังเตรียมพร้อม"
          }
        >
          <p>เนื้อหาจะเปิดให้อ่านเมื่อพร้อมเรียน ลองเลือกหมวดอื่นหรือกลับมาใหม่ได้เสมอ</p>
          <button onClick={() => setParams({})}>ดูทุกหมวด</button>
        </EmptyState>
      )}
      <div className="lesson-grid">
        {visible.map((l, i) => (
          <Reveal key={l.slug}>
            <Link className="lesson-card" to={`/lessons/${l.slug}`}>
              <div className="card-topline">
                <span>บทที่ {String(l.chapter || 2).padStart(2, "0")}</span>
                <ArrowUpRight size={20} />
              </div>
              <div
                className={`chapter-glyphs tone-${(l.chapter || i) % 4}`}
                lang="ja"
              >
                {l.anchors.slice(0, 3).join(" ")}
              </div>
              <p className="eyebrow">
                {
                  learningGroups.find(
                    (g) => g.value === chapterGroup(l.chapter || 2),
                  )?.label
                }
              </p>
              <h2>{l.title_th}</h2>
              <p>{l.summary_th}</p>
              <div className="card-bottom">
                <span>
                  <BookOpen size={15} />
                  {l.available_count} ตัวอักษร
                </span>
                <strong>เปิดบทเรียน →</strong>
              </div>
            </Link>
          </Reveal>
        ))}
      </div>
    </div>
  );
}
