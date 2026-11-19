export interface Kanji {
  character: string;
  meaning_th: string;
  onyomi: string[];
  kunyomi: string[];
  romaji: string;
  strokes: number | null;
  component: string;
  note_th: string;
  source_url: string;
  review_status: string;
}
export interface Lesson {
  private_development?: boolean;
  id: number;
  chapter: number | null;
  is_available: boolean;
  slug: string;
  part: number;
  title_th: string;
  summary_th: string;
  anchors: string[];
  status: "sample" | "needs_review" | "published" | "draft" | "verified";
  available_count: number;
}
export interface LessonDetail extends Lesson {
  private_development?: boolean;
  kanjis: Kanji[];
  introduction_th: string;
  provenance: string;
  sections?: LessonSection[];
}

export interface SourceCard {
  character: string;
  meaning_th: string;
  reading_example: string;
  example: string;
  memory_note: string;
  pdf_page?: number;
  study?: {
    schema_version: number;
    role: "core" | "component" | "supplementary";
    required: boolean;
    reading: {
      kind: string;
      label_th: string;
      form: string;
      reading: string;
      note_th: string;
    };
    example: {
      word: string;
      reading: string;
      meaning_th?: string | null;
      target_scope: string;
      role: string;
      optional: boolean;
    } | null;
    scope_note_th: string;
    mnemonic_note_th: string;
    revision_id?: string;
  };
  editorial_reading_scope?: {
    source_reading: string;
    effective_reading: string;
    scope: string;
    context_forms: string[];
    note: string;
  };
}
export interface ComparisonItem {
  kanji: string;
  reading?: string;
  meaning_th?: string;
  label_th?: string;
  kind?: string;
  study_reading?: {
    kind: string;
    label_th: string;
    form: string;
    reading: string;
  };
}
export interface SectionBlock {
  text?: string;
  practice_count?: number;
  subtitle_th?: string;
  category?: string;
  cards?: SourceCard[];
  pairs?: ComparisonItem[][];
  memory_tips?: string[];
  typed_comparisons?: {
    endpoints: {
      kind: string;
      glyph: string;
      reading?: string;
      meaning_th?: string;
    }[];
  }[];
  diagram?: {
    core: ComparisonItem | null;
    related: ComparisonItem[];
    comparison_pairs: ComparisonItem[][];
  };
  editorial_view?: {
    nodes?: ComparisonItem[];
    pairs?: ComparisonItem[][];
  } | null;
  vocabulary?: {
    word: string;
    reading: string;
    meaning_th: string;
    pdf_page?: number;
    usage_notes?: string;
  }[];
  sentences?: {
    text: string;
    reading: string;
    meaning_th: string;
    note_th: string;
    source_url: string;
  }[];
  comparison_rubric?: {
    model_response_th: string;
    accepted_feature_th: string;
    incorrect_response_th: string;
    max_score: number;
    auto_scorable: boolean;
  };
  instructions_th?: string;
  exercises?: {
    number: number;
    prompt: string;
    pdf_page: number;
    type: string;
  }[];
  exercise_c_prompt?: string;
}
export interface LessonSection {
  kind: string;
  blocks: SectionBlock[];
  pdf_pages?: number[];
}
export interface Health {
  content_mode: string;
  account_writes_enabled?: boolean;
  editorial_preview?: boolean;
}
