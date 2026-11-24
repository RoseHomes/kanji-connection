import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { ChoiceResult } from "./presentation-types";

export type PracticeSubmission = {
  id: string;
  slug: string;
  questionId: string;
  choice: string;
};

function storagePrefix(ownerId: string) {
  return `kanji-connection:practice:${ownerId}:`;
}

export function queuePracticeSubmission(ownerId: string, submission: PracticeSubmission) {
  localStorage.setItem(storagePrefix(ownerId) + submission.id, JSON.stringify(submission));
}

function queuedSubmissions(ownerId: string): PracticeSubmission[] {
  const prefix = storagePrefix(ownerId);
  const submissions: PracticeSubmission[] = [];
  for (const key of Object.keys(localStorage)) {
    if (!key.startsWith(prefix)) continue;
    try {
      const raw = localStorage.getItem(key);
      if (!raw) continue;
      const item = JSON.parse(raw);
      if (
        item && item.id === key.slice(prefix.length) &&
        typeof item.slug === "string" && typeof item.questionId === "string" &&
        typeof item.choice === "string"
      ) submissions.push(item);
    } catch {
      // A malformed entry must not prevent other answers from being recovered.
    }
  }
  return submissions;
}

export async function savePracticeSubmission(ownerId: string, submission: PracticeSubmission) {
  const { slug, questionId, choice, id } = submission;
  const result = await api<ChoiceResult>(
    `/me/practice/${encodeURIComponent(slug)}/${encodeURIComponent(questionId)}/attempt`,
    {
      ownerId,
      method: "POST",
      body: JSON.stringify({ option_id: choice, submission_id: id }),
    },
  );
  if (!result.persisted) throw new Error("เซิร์ฟเวอร์ยังไม่ได้ยืนยันการบันทึก");
  return result;
}

export function usePracticeSaves(
  ownerId: string | undefined,
  onSaved: (id: string, result: ChoiceResult) => void,
) {
  const inFlight = useRef(new Set<string>());
  const [statuses, setStatuses] = useState<Record<string, string | null>>({});
  const send = useCallback(async (submission: PracticeSubmission) => {
    if (!ownerId) return;
    const key = storagePrefix(ownerId) + submission.id;
    if (inFlight.current.has(key)) return;
    inFlight.current.add(key);
    setStatuses((current) => ({ ...current, [key]: null }));
    try {
      const result = await savePracticeSubmission(ownerId, submission);
      onSaved(submission.id, result);
      try {
        localStorage.removeItem(key);
      } catch {
        // The server committed the answer. Leaving the entry permits an idempotent replay.
      }
      setStatuses(({ [key]: _saved, ...remaining }) => remaining);
    } catch (error) {
      setStatuses((current) => ({ ...current, [key]: (error as Error).message }));
    } finally {
      inFlight.current.delete(key);
    }
  }, [onSaved, ownerId]);

  const retry = useCallback(async () => {
    if (!ownerId) return;
    let submissions: PracticeSubmission[];
    try {
      submissions = queuedSubmissions(ownerId);
    } catch {
      return;
    }
    for (const submission of submissions) await send(submission);
  }, [ownerId, send]);

  useEffect(() => {
    const resume = () => void retry();
    resume();
    window.addEventListener("online", resume);
    return () => window.removeEventListener("online", resume);
  }, [retry]);

  const entries = ownerId
    ? Object.entries(statuses).filter(([key]) => key.startsWith(storagePrefix(ownerId)))
    : [];
  return {
    send,
    retry,
    saving: entries.some(([, error]) => error === null),
    error: entries.find(([, error]) => error !== null)?.[1],
  };
}
