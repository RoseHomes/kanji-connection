import { ArrowRight, RotateCcw } from "lucide-react";
import { Link } from "react-router-dom";
import type { Kanji } from "./types";
export function DataState({
  loading,
  error,
  retry,
}: {
  loading: boolean;
  error: Error | null;
  retry: () => void;
}) {
  if (loading && !error)
    return (
      <p className="notice" role="status">
        กำลังโหลดข้อมูล…
      </p>
    );
  if (error)
    return (
      <div className="notice" role="alert">
        <p>{error.message}</p>
        <button onClick={retry}>
          <RotateCcw size={16} /> ลองใหม่
        </button>
        <Link className="text-link" to="/lessons">
          ดูบทเรียนที่เข้าถึงได้
        </Link>
        <small>ลองโหลดใหม่ หรือกลับมาอีกครั้งเมื่อการเชื่อมต่อพร้อม</small>
      </div>
    );
  return null;
}
export function KanjiVisual({
  character,
  meaning,
}: {
  character: string;
  meaning?: string;
}) {
  return (
    <div className="kanji-visual">
      <span lang="ja">{character}</span>
      {meaning && <p>{meaning}</p>}
    </div>
  );
}
export function Reading({ text, reading }: { text: string; reading?: string }) {
  return reading ? (
    <ruby lang="ja">
      {text}
      <rp>（</rp>
      <rt>{reading}</rt>
      <rp>）</rp>
    </ruby>
  ) : (
    <span lang="ja">{text}</span>
  );
}
export function ReadOnlyNotice() {
  return (
    <p className="notice" role="status">
      โหมดอ่านอย่างเดียว · ดูบทเรียนและคำถามได้ แต่ยังไม่เปิดการบันทึกผลหรือซิงก์
    </p>
  );
}
export function PrivateNotice() {
  return <p className="notice">ส่วนตัวสำหรับพัฒนา · ยังไม่ผ่านการอนุมัติเผยแพร่</p>;
}
export function KanjiCard({
  item,
  source,
}: {
  item: Kanji;
  source?: import("./types").SourceCard;
}) {
  return (
    <article className="kanji-card">
      {!["published", "sample", "verified_sample"].includes(
        item.review_status,
      ) && <small className="review-badge">รอตรวจเนื้อหา</small>}
      <KanjiVisual
        character={item.character}
        meaning={source?.meaning_th ?? item.meaning_th}
      />
      <p lang="ja">{item.kunyomi.join(" · ")}</p>
      <small>
        音 <span lang="ja">{item.onyomi.join("・") || "—"}</span> ·{" "}
        {item.strokes === null ? "ยังไม่ระบุจำนวนขีด" : `${item.strokes} ขีด`}
      </small>
      <p>{item.note_th}</p>
      {source && (
        <div className="card-example">
          {source.editorial_reading_scope ? (
            <div className="reading-context">
              <p>
                คำอ่านตามแหล่งข้อมูล:{" "}
                <span lang="ja">
                  {source.editorial_reading_scope.source_reading}
                </span>
              </p>
              <p>
                ดัชนีคำอ่านแยก:{" "}
                <span lang="ja">
                  {source.editorial_reading_scope.effective_reading}
                </span>
              </p>
              <details>
                <summary>หมายเหตุคำอ่านตามบริบท</summary>
                <p lang="en">{source.editorial_reading_scope.note}</p>
                <p lang="ja">
                  {source.editorial_reading_scope.context_forms.join("・")}
                </p>
              </details>
            </div>
          ) : (
            <p>
              <Reading
                text={source.character}
                reading={source.reading_example}
              />
            </p>
          )}
          <p lang="ja">{source.example}</p>
          <p>{source.memory_note}</p>
          <small>PDF หน้า {source.pdf_page}</small>
        </div>
      )}
      {/^https?:\/\//.test(item.source_url) && (
        <a href={item.source_url} target="_blank" rel="noreferrer">
          ดูแหล่งอ้างอิง <ArrowRight size={14} />
        </a>
      )}
    </article>
  );
}
export function SectionTitle({
  eyebrow,
  title,
  to,
}: {
  eyebrow: string;
  title: string;
  to?: string;
}) {
  return (
    <div className="section-title">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      {to && (
        <Link className="text-link" to={to}>
          ดูทั้งหมด <ArrowRight size={17} />
        </Link>
      )}
    </div>
  );
}
export function MemoryIllustration({ count = 1 }: { count?: number }) {
  return (
    <svg
      viewBox="0 0 280 160"
      role="img"
      aria-label={`ภาพช่วยจำต้นไม้ ${count} ต้น`}
      className="tree-art"
    >
      <path
        d="M10 145 Q75 126 140 143 T270 141"
        fill="none"
        stroke="#b4bda0"
        strokeWidth="2"
      />
      {Array.from({ length: count }, (_, i) => {
        const x = count === 1 ? 140 : count === 2 ? 90 + i * 100 : 65 + i * 75;
        const y = i % 2 ? 9 : 0;
        return (
          <g key={i} transform={`translate(${x},${y})`}>
            <path
              d="M0 142V58M0 96L-23 76M0 112L24 88"
              fill="none"
              stroke="#766b4d"
              strokeWidth="5"
              strokeLinecap="round"
            />
            <path
              d="M0 17C-26 20-43 48-34 68C-63 94-24 117 0 99C29 120 59 88 35 68C45 44 25 18 0 17Z"
              fill={i % 2 ? "#a5b494" : "#829975"}
            />
            <path
              d="M0 100V53M0 82L-18 66M0 71L13 59"
              fill="none"
              stroke="#eef0df"
              strokeWidth="2"
              opacity=".65"
            />
          </g>
        );
      })}
      <path
        d="M32 143l-3-8m9 9 3-12m182 10 6-9"
        stroke="#8b9f78"
        strokeWidth="2"
      />
    </svg>
  );
}
