import { describe, expect, it, beforeEach } from "vitest";
import { publicAuthConfig } from "./supabase";
import { requirePublicAuthConfig } from "./auth-config";
import {
  guestSnapshot,
  readGuestLearning,
  saveGuestAttempt,
  saveGuestLesson,
} from "./guest-learning";
import { saveReview } from "./progress";
beforeEach(() => localStorage.clear());
it("rejects private keys before the frontend bundle can be built", () => {
  expect(() =>
    requirePublicAuthConfig(
      "https://project.supabase.co",
      "sb_secret_test_only",
    ),
  ).toThrow("Server secrets");
  expect(() =>
    requirePublicAuthConfig(
      "https://project.supabase.co",
      "sb_publishable_test_only",
    ),
  ).not.toThrow();
});
describe("account configuration", () => {
  it("accepts public keys and rejects server keys and unsafe origins", () => {
    expect(
      publicAuthConfig("https://project.supabase.co", "sb_publishable_test"),
    ).toBe(true);
    expect(
      publicAuthConfig("https://project.supabase.co", "sb_secret_test"),
    ).toBe(false);
    expect(
      publicAuthConfig("http://project.supabase.co", "sb_publishable_test"),
    ).toBe(false);
    const service = `x.${btoa(JSON.stringify({ role: "service_role" }))}.x`;
    expect(publicAuthConfig("https://project.supabase.co", service)).toBe(
      false,
    );
    expect(
      publicAuthConfig(
        "https://project.supabase.co",
        `x.${btoa(JSON.stringify({ role: "anon" }))}.x`,
      ),
    ).toBe(true);
  });
});
it("captures guest reviews, read progress and answers without trusting stored scores", () => {
  saveReview("木", true);
  saveGuestLesson("chapter-02");
  saveGuestAttempt({
    submission_id: crypto.randomUUID(),
    question_key: "chapter-02:q-01",
    answer: "き",
    result: {
      correct: true,
      status: "graded",
      expected: "き",
      explanation: "",
    },
  });
  const snapshot = guestSnapshot();
  expect(snapshot.cards["木"].reviews).toBe(1);
  expect(snapshot.lessons["chapter-02"]).toBe(100);
  expect(snapshot.attempts[0]).not.toHaveProperty("result");
  expect(readGuestLearning().attempts).toHaveLength(1);
  expect(localStorage.getItem("kanji-connection:guest:v1")).not.toBeNull();
});
it("keeps retry submissions unique and recovers from corrupt guest storage", () => {
  const attempt = {
    submission_id: crypto.randomUUID(),
    question_key: "chapter-02:q-01",
    answer: "き",
    result: {
      correct: true,
      status: "graded",
      expected: "き",
      explanation: "",
    },
  };
  saveGuestAttempt(attempt);
  saveGuestAttempt(attempt);
  expect(readGuestLearning().attempts).toHaveLength(1);
  localStorage.setItem("kanji-connection:learning:v1", "broken");
  expect(readGuestLearning().attempts).toEqual([]);
});
