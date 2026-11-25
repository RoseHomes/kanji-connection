import type { Kanji, LessonSection, SourceCard } from "./types";

export type PathKind = "category" | "jlpt";
export type ItemType = "kanji" | "vocabulary" | "sentence";
type Counts = Record<ItemType, number>;

export interface LearningPath {
  kind: PathKind;
  slug: string;
  title_th: string;
  summary_th: string;
  level: number | null;
  counts: Counts;
  reference: {
    source_key: string;
    source_url: string;
    version: string;
    license: string;
    attribution: string;
    totals: Counts;
  } | null;
}

interface UnitSummary {
  unit_key: string;
  title_th: string;
  intro_th: string;
  available_count: number;
}

export interface PathDetail extends LearningPath {
  units: UnitSummary[];
}

interface ItemBase {
  id: number;
  text: string;
  meaning_th: string;
  context_note_th: string;
  level: number | null;
  unit_key: string | null;
  path_slug: string;
  required: boolean;
}

export type LearningItem = ItemBase &
  (
    | { type: "kanji"; kanji: Kanji }
    | { type: "vocabulary" | "sentence"; reading: string; usage_notes: string }
  );

export interface ItemPage {
  items: LearningItem[];
  next_cursor: string | null;
  total: number;
}

export interface LearningUnit extends UnitSummary {
  path: LearningPath;
  items: LearningItem[];
  previous_unit_key: string | null;
  next_unit_key: string | null;
  practice_available: boolean;
}

export const pathInfo = {
  category: { base: "/categories", title: "เรียนตามหมวด" },
  jlpt: { base: "/jlpt", title: "เตรียม JLPT" },
} as const;

export function unitLesson(unit: LearningUnit) {
  const kanjis: Kanji[] = [];
  const cards: SourceCard[] = [];
  const words = [];
  const sentences = [];
  for (const item of unit.items) {
    if (item.type === "kanji") {
      const kanji = item.kanji;
      const reading = kanji.onyomi[0] || kanji.kunyomi[0] || "";
      kanjis.push(kanji);
      cards.push({
        content_id: item.id,
        character: kanji.character,
        meaning_th: kanji.meaning_th,
        reading_example: reading,
        example: "",
        memory_note: kanji.note_th,
        ...(reading && {
          study: {
            schema_version: 2,
            role: "core",
            required: item.required,
            reading: {
              kind: "character",
              label_th: kanji.onyomi.length ? "音読み" : "訓読み",
              form: kanji.character,
              reading,
              note_th: "",
            },
            example: null,
            scope_note_th: item.context_note_th,
            mnemonic_note_th: "",
          },
        }),
      });
    } else if (item.type === "vocabulary") {
      words.push({
        word: item.text,
        reading: item.reading,
        meaning_th: item.meaning_th,
        usage_notes: [item.usage_notes, item.context_note_th]
          .filter(Boolean)
          .join("\n"),
      });
    } else {
      sentences.push({
        text: item.text,
        reading: item.reading,
        meaning_th: item.meaning_th,
        note_th: [item.usage_notes, item.context_note_th]
          .filter(Boolean)
          .join("\n"),
        source_url: "",
      });
    }
  }
  const sections: LessonSection[] = [];
  if (cards.length) sections.push({ kind: "cards", blocks: [{ cards }] });
  if (words.length || sentences.length) {
    sections.push({
      kind: "vocabulary",
      blocks: [{ vocabulary: words, sentences }],
    });
  }
  return {
    slug: `${unit.path.kind}:${unit.path.slug}:${unit.unit_key}`,
    title_th: unit.title_th,
    summary_th: unit.path.summary_th,
    introduction_th: unit.intro_th,
    status: "published" as const,
    anchors: kanjis.map((item) => item.character),
    kanjis,
    sections,
  };
}
