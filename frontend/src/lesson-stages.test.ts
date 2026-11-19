import { describe, expect, it, vi, afterEach } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  deriveStages,
  resolveStage,
  readPosition,
  writePosition,
} from "./lesson-stages";
import { safeLessonReturn } from "./lesson-return";
import type { LessonDetail, Kanji, SectionBlock } from "./types";
const path = resolve(process.cwd(), "../private/hybrid-learning/baseline.json");
const baseline = existsSync(path)
  ? JSON.parse(readFileSync(path, "utf8"))
  : null;
const fixture = (count: number) =>
  ({
    slug: "sample",
    title_th: "ตัวอย่าง",
    summary_th: "สังเกตรูป",
    introduction_th: "สังเกต",
    anchors: [],
    kanjis: Array.from(
      { length: count },
      (_, i) =>
        ({
          character: String.fromCharCode(0x4e00 + i),
          meaning_th: "fixture",
          kunyomi: ["き"],
          onyomi: [],
          note_th: "source",
        }) as unknown as Kanji,
    ),
    sections: [],
  }) as unknown as LessonDetail;
afterEach(() => {
  sessionStorage.clear();
  vi.restoreAllMocks();
});
describe.skipIf(!baseline)("working-edition stage accounting", () => {
  it.each(Array.from({ length: 30 }, (_, i) => i))(
    "preserves every instructional unit exactly once in chapter %i",
    (i) => {
      const lesson = baseline.lessons[i] as LessonDetail,
        original = JSON.stringify(lesson),
        stages = deriveStages(lesson);
      const expected = lesson.sections!.flatMap((s) =>
        s.blocks.flatMap((b) => b.cards || []),
      );
      expect(stages.flatMap((s) => s.cards)).toEqual(expected);
      expect(expected).toHaveLength(14);
      expect(
        stages
          .filter((s) => s.cards.length)
          .every((s) => s.cards.length >= 2 && s.cards.length <= 4),
      ).toBe(true);
      const units = stages.flatMap((s) => s.units);
      expect(new Set(units).size).toBe(units.length);
      const expectedUnits: string[] = [];
      const expectedBlocks: SectionBlock[] = [];
      lesson.sections!.forEach((s, si) =>
        s.blocks.forEach((b, bi) => {
          b.cards?.forEach((_, ci) =>
            expectedUnits.push(`${si}:${bi}:card:${ci}`),
          );
          const rest = { ...b };
          delete rest.cards;
          if (Object.keys(rest).length) {
            expectedUnits.push(`${si}:${bi}:block`);
            expectedBlocks.push(rest);
          }
        }),
      );
      expect([...units].sort()).toEqual(expectedUnits.sort());
      const actual = stages
        .flatMap((s) => s.sections.flatMap((s) => s.blocks))
        .filter((b) => !b.cards);
      expect(actual.map((b) => JSON.stringify(b)).sort()).toEqual(
        expectedBlocks.map((b) => JSON.stringify(b)).sort(),
      );
      expect(JSON.stringify(lesson)).toBe(original);
    },
  );
  it("retains all 420 occurrences and all five verified sentences", () => {
    const stages = baseline.lessons.flatMap((l: LessonDetail) =>
      deriveStages(l),
    );
    expect(
      stages.flatMap((s: ReturnType<typeof deriveStages>[number]) => s.cards),
    ).toHaveLength(420);
    expect(
      stages.flatMap((s: ReturnType<typeof deriveStages>[number]) =>
        s.sections.flatMap((s) => s.blocks.flatMap((b) => b.sentences || [])),
      ),
    ).toHaveLength(5);
  });
});
it.each([1, 2, 3, 4, 5, 7, 9, 13, 14, 17])(
  "balances %i cards without orphan or singleton leftovers",
  (count) => {
    const stages = deriveStages(fixture(count)),
      groups = stages.filter((s) => s.cards.length);
    expect(groups.flatMap((s) => s.cards)).toHaveLength(count);
    expect(
      groups.every(
        (s) => s.cards.length <= 4 && (count === 1 || s.cards.length >= 2),
      ),
    ).toBe(true);
    expect(stages.some((s) => s.phase === "connect")).toBe(false);
  },
);
it("recovers invalid or removed stages predictably", () => {
  const stages = deriveStages(fixture(14));
  expect(resolveStage(stages, "learn-999").id).toBe("learn-4");
  expect(resolveStage(stages, "removed").id).toBe("discover");
  expect(resolveStage(stages, "learn-0").id).toBe("learn-1");
});
it("stores position and visits only, never learning records or scores", () => {
  writePosition("sample", {
    mode: "guided",
    stage: "learn-1",
    visited: ["discover", "learn-1"],
  });
  expect(readPosition("sample")).toEqual({
    mode: "guided",
    stage: "learn-1",
    visited: ["discover", "learn-1"],
  });
  expect(sessionStorage.getItem("kanji:lesson-position:v1:sample")).not.toMatch(
    /answer|score|meaning|reading/,
  );
});
it("continues safely when session storage is blocked or corrupted", () => {
  sessionStorage.setItem("kanji:lesson-position:v1:sample", "invalid");
  expect(readPosition("sample")).toBeNull();
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  expect(() =>
    writePosition("sample", { mode: "full", stage: "use", visited: [] }),
  ).not.toThrow();
});
it("restricts return links to internal lesson paths and the expected chapter", () => {
  expect(
    safeLessonReturn(
      "/lessons/chapter-01?mode=guided&stage=learn-2",
      "chapter-01",
    ),
  ).toContain("learn-2");
  for (const value of [
    "https://evil.example/lessons/chapter-01",
    "//evil.example",
    "javascript:alert(1)",
    "/account",
    "/lessons/../account",
  ]) {
    expect(safeLessonReturn(value)).toBeNull();
  }
  expect(safeLessonReturn("/lessons/chapter-02", "chapter-01")).toBeNull();
});
