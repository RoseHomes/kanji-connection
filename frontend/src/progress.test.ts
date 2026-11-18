import { beforeEach, describe, expect, it } from "vitest";
import { readProgress, saveReview, schedule } from "./progress";
beforeEach(() => localStorage.clear());
describe("deterministic review scheduling", () => {
  const now = new Date("2026-11-13T00:00:00Z");
  it("starts at one day, doubles successful intervals, and caps at ninety", () => {
    const first = schedule(undefined, true, now);
    expect(first.due).toBe("2026-11-14T00:00:00.000Z");
    expect(schedule(first, true, now).interval).toBe(2);
    expect(schedule({ ...first, interval: 80 }, true, now).interval).toBe(90);
  });
  it("resets lapses and persists across reads", () => {
    const previous = schedule(undefined, true, now);
    const lapse = schedule({ ...previous, interval: 8 }, false, now);
    expect(lapse.interval).toBe(1);
    expect(lapse.lapses).toBe(1);
    expect(saveReview("木", false, now)).toBe(true);
    expect(readProgress().cards["木"]).toEqual({ ...lapse, reviews: 1 });
  });
  it("recovers from corrupted and unsupported stored records", () => {
    localStorage.setItem("kanji-connection:guest:v1", "broken");
    expect(readProgress().cards).toEqual({});
    localStorage.setItem(
      "kanji-connection:guest:v1",
      JSON.stringify({ version: 1, cards: { 木: { due: "never" } } }),
    );
    expect(readProgress().cards).toEqual({});
  });
});
