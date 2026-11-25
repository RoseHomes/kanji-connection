import { ArrowRight, RotateCcw, BookOpen, LockKeyhole } from "lucide-react";
import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import type { Kanji } from "./types";
import type { ComparisonCharacter } from "./presentation-types";
import { StudyContent } from "./study-content";
import { useLessonReturn, withLessonReturn } from "./lesson-return";
import {
  AudioText,
  KanjiAudioReadings,
  KanjiReadingList,
  LessonAudioRow,
  type LessonAudioKind,
} from "./lesson-audio";
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
export function Reading({ text, reading, audioKind, slug }: {
  text: string;
  reading?: string;
  audioKind?: LessonAudioKind;
  slug?: string;
}) {
  const label = reading ? (
    <ruby lang="ja">
      {text}
      <rp>（</rp>
      <rt>{reading}</rt>
      <rp>）</rp>
    </ruby>
  ) : (
    <span lang="ja">{text}</span>
  );
  return audioKind ? (
    <LessonAudioRow clip={{ kind: audioKind, text, reading, slug }}>
      {label}
    </LessonAudioRow>
  ) : (
    label
  );
}
export function ReadingAudioRow({ text, reading, kind, slug, children }: {
  text: string;
  reading?: string;
  kind: LessonAudioKind;
  slug?: string;
  children?: ReactNode;
}) {
  return (
    <LessonAudioRow as="div" clip={{ kind, text, reading, slug }}>
      <Reading text={text} reading={reading} />
      {children}
    </LessonAudioRow>
  );
}

export function ComparisonReading({ item, slug, children }: {
  item: ComparisonCharacter;
  slug: string;
  children?: ReactNode;
}) {
  const { reading } = item;
  if (reading.kind === "component") {
    return (
      <LessonAudioRow as="div" clip={{
        kind: "component", text: reading.form || item.character,
        reading: reading.reading, slug, fallbackKind: reading.form ? undefined : "kanji",
      }}
      >
        <span lang="ja">{reading.reading}</span>
        {children}
      </LessonAudioRow>
    );
  }
  return (
    <ReadingAudioRow text={reading.form} reading={reading.reading} kind={reading.kind === "word" ? "word" : "kanji"} slug={slug}>
      {children}
    </ReadingAudioRow>
  );
}
export function ReadOnlyNotice() {
  return (
    <p className="notice" role="status">
      โหมดอ่านอย่างเดียว · เรียนและทำแบบฝึกหัดได้ แต่ยังไม่เปิดการบันทึกผลหรือซิงก์
    </p>
  );
}
export function AccountGate({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="page section gate-page">
      <div className="access-card">
        <span className="icon-tile">
          <LockKeyhole size={24} />
        </span>
        <p className="eyebrow">YOUR PERSONAL SPACE</p>
        <h1>{title}</h1>
        <p className="lead">{description}</p>
        <p>บทเรียน คันจิ และแบบฝึกหัดที่เผยแพร่แล้ว เปิดให้เรียนได้โดยไม่ต้องมีบัญชี</p>
        <div className="hero-actions">
          <Link className="button primary" to="/account">
            เข้าสู่ระบบ <ArrowRight size={17} />
          </Link>
          <Link className="button" to="/lessons">
            เรียนโดยไม่เข้าสู่ระบบ
          </Link>
        </div>
      </div>
    </div>
  );
}
export function EmptyState({
  title,
  children,
}: {
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="empty-state" role="status">
      <span className="icon-tile">
        <BookOpen size={25} />
      </span>
      <h2>{title}</h2>
      <div>{children}</div>
    </div>
  );
}
export function PrivateNotice() {
  return <p className="notice">พื้นที่ทดลองเรียนส่วนตัว · เนื้อหายังไม่เปิดสาธารณะ</p>;
}
export function KanjiCard({
  item,
  source,
  focused = false,
  allowDetail = false,
}: {
  item: Kanji;
  source?: import("./types").SourceCard;
  focused?: boolean;
  allowDetail?: boolean;
}) {
  const returnTo = useLessonReturn();
  const example = source?.example.match(/^(.+?)\s+([\p{Script=Hiragana}\p{Script=Katakana}ー]+)$/u);
  return (
    <article
      className={`kanji-card${source?.study?.role === "supplementary" ? " supplementary-card" : ""}`}
      data-study-role={source?.study?.role}
    >
      {!["published", "sample", "verified_sample"].includes(
        item.review_status,
      ) &&
        source?.study?.role === "supplementary" && (
          <small className="supplement-label">เลือกเรียนได้</small>
        )}
      <KanjiVisual
        character={item.character}
        meaning={source?.meaning_th ?? item.meaning_th}
      />
      {!source?.study && !!item.kunyomi.length && <p><KanjiReadingList character={item.character} readings={item.kunyomi} /></p>}
      {!source?.study && (
        <small>
          <span lang="ja">音</span>
          <KanjiReadingList character={item.character} readings={item.onyomi} />
          {item.strokes === null ? "ยังไม่ระบุจำนวนขีด" : `${item.strokes} ขีด`}
        </small>
      )}
      <p><AudioText text={item.note_th} /></p>
      {source?.study && <StudyContent card={source} focused={focused} />}
      {source?.study && <KanjiAudioReadings
        character={item.character}
        onyomi={item.onyomi}
        kunyomi={item.kunyomi}
        primary={source?.study?.reading.kind === "character"
          ? source.study.reading.reading
          : undefined}
      />}
      {source && !source.study && (
        <div className="card-example">
          <small>ตัวอย่างคำที่ใช้ตัวอักษรนี้</small>
          <p><LessonAudioRow clip={example ? { kind: "word", text: example[1], reading: example[2] } : undefined}>
            <span lang="ja">{source.example}</span>
          </LessonAudioRow></p>
          <p><AudioText text={source.memory_note} /></p>
        </div>
      )}
      {/^https?:\/\//.test(item.source_url) && (
        <a href={item.source_url} target="_blank" rel="noreferrer">
          ดูแหล่งอ้างอิง <ArrowRight size={14} />
        </a>
      )}
      {(allowDetail ||
        ["published", "sample", "verified_sample"].includes(
          item.review_status,
        )) && (
        <Link
          className="card-detail-link"
          to={withLessonReturn(
            `/explore/${encodeURIComponent(item.character)}`,
            returnTo,
          )}
        >
          ดูรายละเอียด <span lang="ja">{item.character}</span>
          <ArrowRight size={16} />
        </Link>
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
