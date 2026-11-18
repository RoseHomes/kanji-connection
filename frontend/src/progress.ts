export interface ReviewRecord {
  interval: number;
  due: string;
  reviews: number;
  lapses: number;
}
interface Progress {
  version: 1;
  cards: Record<string, ReviewRecord>;
}
const KEY = "kanji-connection:guest:v1";
export function schedule(
  previous: ReviewRecord | undefined,
  knew: boolean,
  now: Date,
): ReviewRecord {
  const interval = knew
    ? Math.min(90, previous ? Math.max(1, previous.interval * 2) : 1)
    : 1;
  return {
    interval,
    due: new Date(now.getTime() + interval * 86400000).toISOString(),
    reviews: (previous?.reviews || 0) + 1,
    lapses: (previous?.lapses || 0) + (knew ? 0 : 1),
  };
}
export function readProgress(): Progress {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || "null");
    if (
      raw?.version === 1 &&
      raw.cards &&
      typeof raw.cards === "object" &&
      !Array.isArray(raw.cards)
    ) {
      const cards: Record<string, ReviewRecord> = {};
      for (const [key, v] of Object.entries(raw.cards)) {
        const r = v as ReviewRecord;
        if (
          r &&
          Number.isFinite(r.interval) &&
          r.interval >= 1 &&
          r.interval <= 90 &&
          Number.isInteger(r.reviews) &&
          r.reviews >= 0 &&
          Number.isInteger(r.lapses) &&
          r.lapses >= 0 &&
          typeof r.due === "string" &&
          Number.isFinite(Date.parse(r.due))
        )
          cards[key] = r;
      }
      return { version: 1, cards };
    }
  } catch {
    /* Ignore corrupt or unavailable browser storage. */
  }
  return { version: 1, cards: {} };
}
export function saveReview(
  character: string,
  knew: boolean,
  now = new Date(),
): boolean {
  const p = readProgress();
  p.cards[character] = schedule(p.cards[character], knew, now);
  try {
    localStorage.setItem(KEY, JSON.stringify(p));
    return true;
  } catch {
    return false;
  }
}
