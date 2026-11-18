import { readProgress } from "./progress";
export interface QuizResult {
  correct: boolean | null;
  status: string;
  expected: string | null;
  explanation: string;
  persisted?: boolean;
}
export interface GuestAttempt {
  submission_id: string;
  question_key: string;
  answer: string;
  result: QuizResult;
}
interface GuestLearning {
  version: 1;
  lessons: Record<string, number>;
  attempts: GuestAttempt[];
}
const KEY = "kanji-connection:learning:v1";
export function readGuestLearning(): GuestLearning {
  try {
    const value = JSON.parse(localStorage.getItem(KEY) || "null");
    if (
      value?.version === 1 &&
      value.lessons &&
      Array.isArray(value.attempts)
    ) {
      const lessons = Object.fromEntries(
        Object.entries(value.lessons).filter(
          ([k, v]) =>
            /^chapter-\d{2}$/.test(k) &&
            Number.isInteger(v) &&
            (v as number) >= 0 &&
            (v as number) <= 100,
        ),
      ) as Record<string, number>;
      const attempts = value.attempts
        .filter(
          (a: GuestAttempt) =>
            a &&
            typeof a.submission_id === "string" &&
            typeof a.question_key === "string" &&
            typeof a.answer === "string" &&
            a.result &&
            typeof a.result.status === "string",
        )
        .slice(-200);
      return { version: 1, lessons, attempts };
    }
  } catch {
    /* Keep the original storage unchanged when unavailable/corrupt. */
  }
  return { version: 1, lessons: {}, attempts: [] };
}
function store(data: GuestLearning) {
  try {
    localStorage.setItem(KEY, JSON.stringify(data));
    return true;
  } catch {
    return false;
  }
}
export function saveGuestLesson(slug: string) {
  const data = readGuestLearning();
  data.lessons[slug] = 100;
  return store(data);
}
export function saveGuestAttempt(attempt: GuestAttempt) {
  const data = readGuestLearning();
  data.attempts = [
    ...data.attempts.filter((a) => a.submission_id !== attempt.submission_id),
    attempt,
  ].slice(-200);
  return store(data);
}
export function guestSnapshot() {
  const data = readGuestLearning();
  return {
    cards: readProgress().cards,
    lessons: data.lessons,
    attempts: data.attempts.map(({ submission_id, question_key, answer }) => ({
      submission_id,
      question_key,
      answer,
    })),
  };
}
