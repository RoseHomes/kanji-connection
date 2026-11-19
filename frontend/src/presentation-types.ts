export interface Choice {
  id: string;
  text: string;
}
export interface PracticeQuestion {
  id: string;
  prompt: string;
  kind: string;
  options: Choice[];
}
export interface ChoiceResult {
  correct: boolean;
  correct_option_id: string;
  correct_text: string;
  explanation: string;
  selection_explanation: string;
  persisted: false;
}
export interface ComparisonCharacter {
  character: string;
  meaning_th: string;
  memory_note: string;
  reading: { form: string; reading: string; label_th: string; kind?: string };
  example: {
    word: string;
    reading: string;
    meaning_th?: string;
    optional?: boolean;
    target_scope?: string;
  } | null;
}
export interface ComparisonGroup {
  id: string;
  title: string;
  chapter: number;
  slug: string;
  category: string;
  difference_th: string;
  characters: ComparisonCharacter[];
}
export const learningGroups = [
  { value: "all", label: "ทั้งหมด" },
  { value: "basic", label: "รูปพื้นฐาน" },
  { value: "similar", label: "ตัวคล้ายกัน" },
  { value: "component", label: "ส่วนประกอบ" },
  { value: "everyday", label: "คันจิใช้งาน" },
  { value: "review", label: "ทบทวน" },
];
export function chapterGroup(chapter: number) {
  return chapter <= 10
    ? "basic"
    : chapter <= 15
      ? "similar"
      : chapter <= 25
        ? "component"
        : chapter <= 29
          ? "everyday"
          : "review";
}
