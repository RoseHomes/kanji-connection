import { describe, expect, it } from "vitest";
import { type LearningUnit, unitLesson } from "./learning-paths";
import { deriveStages, readPosition, writePosition } from "./lesson-stages";

const unit: LearningUnit = {
  unit_key: "people-and-time",
  title_th: "นับคนและเวลา",
  intro_th: "",
  available_count: 1,
  path: {
    kind: "category",
    slug: "japanese-counters",
    title_th: "ลักษณนามญี่ปุ่น",
    summary_th: "",
    counts: { kanji: 0, vocabulary: 1, sentence: 0 },
    level: null,
    reference: null,
  },
  items: [
    {
      type: "vocabulary",
      id: 10,
      text: "一人",
      reading: "ひとり",
      meaning_th: "หนึ่งคน",
      usage_notes: "",
      context_note_th: "",
      required: true,
      level: null,
      path_slug: "japanese-counters",
      unit_key: "people-and-time",
    },
  ],
  previous_unit_key: null,
  next_unit_key: null,
  practice_available: false,
};

describe("existing lesson presentation with path units", () => {
  it("derives learn and review stages for a vocabulary-only unit", () => {
    const lesson = unitLesson(unit);
    const stages = deriveStages(lesson, { isUnit: true });
    expect(lesson).not.toHaveProperty("chapter");
    expect(stages.map(({ id }) => id)).toEqual(["discover", "use", "review"]);
    expect(stages[1].sections[0].blocks[0].vocabulary?.[0]).toMatchObject({
      word: "一人",
      reading: "ひとり",
    });
  });

  it("keeps a unit position separate from the old lesson position", () => {
    const { slug } = unitLesson(unit);
    writePosition(slug, { mode: "guided", stage: "discover", visited: [] });
    writePosition(slug, { mode: "full", stage: "use", visited: ["use"] }, true);
    expect(readPosition(slug)?.mode).toBe("guided");
    expect(readPosition(slug, true)).toMatchObject({
      mode: "full",
      stage: "use",
    });
  });
});
