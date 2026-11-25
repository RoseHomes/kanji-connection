import type { LessonDetail, LessonSection, SourceCard } from "./types";

export type Phase = "discover" | "learn" | "connect" | "check" | "review";
export interface LessonStage {
  id: string;
  phase: Phase;
  title: string;
  focus: string;
  sections: LessonSection[];
  units: string[];
  sourceSections: number[];
  cards: SourceCard[];
}
export const phases: { id: Phase; label: string; hint: string }[] = [
  { id: "discover", label: "เริ่มสังเกต", hint: "รู้จักบทนี้" },
  { id: "learn", label: "เรียนทีละกลุ่ม", hint: "รูป · คำ · ภาพจำ" },
  { id: "connect", label: "เชื่อมและเทียบ", hint: "เห็นความต่าง" },
  { id: "check", label: "ลองเช็ก", hint: "ข้ามได้เสมอ" },
  { id: "review", label: "ทวนและฝึก", hint: "เลือกทางต่อไป" },
];

/** Read-only presentation derivation. Contiguous source order is retained;
 * each card and each non-card block is assigned once, never rewritten. */
export function deriveStages<T extends Pick<LessonDetail, "introduction_th" | "summary_th" | "sections" | "kanjis">>(
  lesson: T,
  { isUnit = false }: { isUnit?: boolean } = {},
): LessonStage[] {
  const intro: LessonStage = {
    id: "discover",
    phase: "discover",
    title: "เริ่มจากสิ่งที่ควรสังเกต",
    focus: lesson.introduction_th || lesson.summary_th,
    sections: [],
    units: [],
    sourceSections: [],
    cards: [],
  };
  const connect: LessonStage = {
    id: "connect",
    phase: "connect",
    title: "วางข้างกัน แล้วเชื่อมความเข้าใจ",
    focus: "ดูรูปและความสัมพันธ์ที่เรียนในบทนี้ ก่อนเลือกคู่ที่อยากเทียบเพิ่ม",
    sections: [],
    units: [],
    sourceSections: [],
    cards: [],
  };
  const use: LessonStage = {
    id: "use",
    phase: "learn",
    title: "ลองอ่านเป็นคำ แล้วดูการใช้",
    focus: "อ่านทั้งคำพร้อมความหมาย ดูตัวอย่างเสริมได้ตามความสนใจ",
    sections: [],
    units: [],
    sourceSections: [],
    cards: [],
  };
  const review: LessonStage = {
    id: "review",
    phase: "review",
    title: "ทวนสิ่งที่พบ แล้วเลือกฝึกต่อ",
    focus: isUnit
      ? "ทวนคำและตัวอย่างที่เพิ่งเรียน"
      : "กลับไปดูกลุ่มที่ยังสับสน หรือเริ่มแบบฝึกหัดประจำบทได้ทันที",
    sections: [],
    units: [],
    sourceSections: [],
    cards: [],
  };
  const learning: LessonStage[] = [];
  (lesson.sections || []).forEach((section, si) =>
    section.blocks.forEach((block, bi) => {
      if (block.cards?.length) {
        // Divide seven-card source sets into 4+3, never a final one-card step.
        let remainingGroups = Math.ceil(block.cards.length / 4);
        for (let offset = 0; offset < block.cards.length;) {
          const size = Math.ceil(
            (block.cards.length - offset) / remainingGroups--,
          );
          const cards = block.cards.slice(offset, offset + size),
            id = cards[0].content_id === undefined
              ? `learn-${learning.length + 1}`
              : `learn-item-${cards[0].content_id}`;
          learning.push({
            id,
            phase: "learn",
            title: `กลุ่ม ${learning.length + 1} · ${cards.map((c) => c.character).join(" · ")}`,
            focus: `${isUnit ? "สังเกตรูปและคำอ่านของ" : "สังเกตรูป คำอ่าน และภาพช่วยจำของ"} ${cards.map((c) => c.character).join(" · ")}`,
            cards,
            sections: [{ kind: "cards", blocks: [{ cards }] }],
            units: cards.map((_, i) => `${si}:${bi}:card:${offset + i}`),
            sourceSections: [si],
          });
          offset += size;
        }
      }
      const rest = { ...block };
      delete rest.cards;
      if (Object.keys(rest).length) {
        const target =
          section.kind === "introduction"
            ? intro
            : section.kind === "comparison" || section.kind === "mnemonic"
              ? connect
              : section.kind === "exercises"
                ? review
                : use;
        target.sections.push({ kind: section.kind, blocks: [rest] });
        target.units.push(`${si}:${bi}:block`);
        target.sourceSections.push(si);
      }
    }),
  );
  if (!learning.length && lesson.kanjis.length) {
    const cards = lesson.kanjis.map((k) => ({
      character: k.character,
      meaning_th: k.meaning_th,
      reading_example: k.kunyomi[0] || k.onyomi[0] || "",
      example: "",
      memory_note: k.note_th,
    }));
    let remainingGroups = Math.ceil(cards.length / 4);
    for (let i = 0; i < cards.length;) {
      const size = Math.ceil((cards.length - i) / remainingGroups--);
      const group = cards.slice(i, i + size);
      learning.push({
        id: `learn-${learning.length + 1}`,
        phase: "learn",
        title: `กลุ่ม ${learning.length + 1} · ${group.map((c) => c.character).join(" · ")}`,
        focus: "อ่านคำและความหมาย แล้วสังเกตรูปที่เห็น",
        cards: group,
        sections: [{ kind: "cards", blocks: [{ cards: group }] }],
        units: group.map((_, j) => `fallback:card:${i + j}`),
        sourceSections: [],
      });
      i += size;
    }
  }
  const check: LessonStage = {
    id: "check",
    phase: "check",
    title: "ลองเช็กความเข้าใจสั้น ๆ",
    focus:
      "ใช้คำถามเดิมจากชุดฝึกประจำบท ไม่เพิ่มข้อสอบและไม่บันทึกคะแนน ข้ามได้โดยไม่ต้องตอบถูก",
    sections: [],
    cards: [],
    units: [],
    sourceSections: [],
  };
  return [
    intro,
    ...learning,
    ...(use.sections.length ? [use] : []),
    ...(connect.sections.length ? [connect] : []),
    ...(!isUnit && lesson.kanjis.length ? [check] : []),
    review,
  ];
}

export function resolveStage(stages: LessonStage[], requested: string | null) {
  const exact = stages.find((s) => s.id === requested);
  if (exact) return exact;
  const match = requested?.match(/^learn-(\d+)$/);
  if (match) {
    const groups = stages.filter((s) => s.cards.length);
    return (
      groups[Math.max(0, Math.min(groups.length - 1, Number(match[1]) - 1))] ||
      stages[0]
    );
  }
  return stages[0];
}

export interface LessonPosition {
  mode: "guided" | "full";
  stage: string;
  visited: string[];
  card?: number;
  item?: number;
}
const key = (slug: string, unit: boolean) =>
  `kanji:${unit ? "unit" : "lesson"}-position:v1:${slug}`;
export function readPosition(slug: string, unit = false): LessonPosition | null {
  try {
    const p = JSON.parse(sessionStorage.getItem(key(slug, unit)) || "null");
    return p &&
      ["guided", "full"].includes(p.mode) &&
      typeof p.stage === "string" &&
      Array.isArray(p.visited)
      ? {
          mode: p.mode,
          stage: p.stage,
          visited: p.visited.filter((s: unknown) => typeof s === "string"),
          ...(Number.isInteger(p.card) && p.card >= 0 && p.card < 4
            ? { card: p.card }
            : {}),
          ...(unit && Number.isSafeInteger(p.item) && p.item > 0 ? { item: p.item } : {}),
        }
      : null;
  } catch {
    return null;
  }
}
export function writePosition(slug: string, value: LessonPosition, unit = false) {
  try {
    sessionStorage.setItem(key(slug, unit), JSON.stringify(value));
  } catch {
    /* Storage restrictions never block learning. */
  }
}
