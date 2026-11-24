import { useQuery } from "@tanstack/react-query";
import { Square, Volume2 } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

export type LessonAudioKind =
  "kanji" | "component" | "word" | "sentence" | "term" | "quiz_choice";
export const JAPANESE_AUDIO_ATTRIBUTION = "VOICEVOX:四国めたん";
const bucket = "kanji-japanese-audio";
const indexPath = "/assets/japanese-audio-index.json";
const timeoutMs = 12_000;

interface PlaybackIndex {
  version: number;
  bucket: string;
  attribution: string;
  lessons: Record<string, Record<string, string>>;
  shared: Record<string, string>;
  files: Record<string, string>;
}

async function getIndex() {
  const response = await fetch(indexPath);
  if (
    !response.ok ||
    response.headers.get("content-type")?.includes("text/html")
  )
    throw new Error("Japanese audio index is unavailable");
  const index = (await response.json()) as PlaybackIndex;
  if (
    index.version !== 2 ||
    index.bucket !== bucket ||
    index.attribution !== JAPANESE_AUDIO_ATTRIBUTION ||
    !index.shared || !index.lessons || !index.files
  )
    throw new Error("Invalid Japanese audio index");
  return index;
}

export async function audioLookupKey(
  kind: LessonAudioKind,
  text: string,
  reading: string,
) {
  const bytes = new TextEncoder().encode(
    [kind, text.trim(), normalizeReading(reading)].join("\x1f"),
  );
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash).slice(0, 16), (value) =>
    value.toString(16).padStart(2, "0"),
  ).join("");
}

function normalizeReading(reading: string) {
  return reading
    .trim()
    .normalize("NFC")
    .replace(/[ァ-ヶ]/g, (character) =>
      String.fromCharCode(character.charCodeAt(0) - 0x60),
    )
    .replaceAll(".", "");
}

type PlaybackState = {
  control: string;
  phase: "loading" | "playing" | "error";
} | null;
interface AudioContextValue {
  index: PlaybackIndex;
  slug?: string;
  quizOnly: boolean;
  origin: string;
  state: PlaybackState;
  toggle: (control: string, url: string) => void;
  stop: () => void;
}
const LessonAudioContext = createContext<AudioContextValue | null>(null);

export function useLessonAudioAvailable() {
  return useContext(LessonAudioContext) !== null;
}

export function LessonAudio({
  slug,
  enabled,
  quizOnly = false,
  playbackScope,
  children,
}: {
  slug?: string;
  enabled: boolean;
  quizOnly?: boolean;
  playbackScope: string;
  children: ReactNode;
}) {
  const origin = (import.meta.env.VITE_SUPABASE_URL || "").replace(/\/$/, "");
  const active = enabled && /^https:\/\/[a-z0-9]+\.supabase\.co$/.test(origin);
  const index = useQuery({
    queryKey: ["japanese-lesson-audio-index"],
    queryFn: getIndex,
    enabled: active,
    staleTime: Infinity,
    retry: false,
  });
  const current = useRef<{
    element: HTMLAudioElement;
    control: string;
    timer?: number;
  } | null>(null);
  const [state, setState] = useState<PlaybackState>(null);

  const release = useCallback(() => {
    const session = current.current;
    current.current = null;
    if (!session) return;
    window.clearTimeout(session.timer);
    const audio = session.element;
    audio.onended = audio.onerror = audio.onwaiting = audio.onplaying = null;
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
  }, []);

  const stop = useCallback(() => {
    release();
    setState(null);
  }, [release]);

  useLayoutEffect(() => {
    setState(null);
    return release;
  }, [active, playbackScope, release, slug, quizOnly]);

  function toggle(control: string, url: string) {
    const sameControl = current.current?.control === control;
    release();
    if (sameControl) {
      setState(null);
      return;
    }
    const audio = new Audio(url);
    const session = {
      element: audio,
      control,
      timer: undefined as number | undefined,
    };
    current.current = session;
    const finish = (error: boolean) => {
      if (current.current !== session) return;
      release();
      setState(error ? { control, phase: "error" } : null);
    };
    function loading() {
      if (current.current !== session) return;
      window.clearTimeout(session.timer);
      session.timer = window.setTimeout(() => finish(true), timeoutMs);
      setState({ control, phase: "loading" });
    }
    audio.onwaiting = loading;
    audio.onplaying = () => {
      if (current.current !== session) return;
      window.clearTimeout(session.timer);
      setState({ control, phase: "playing" });
    };
    audio.onended = () => finish(false);
    audio.onerror = () => finish(true);
    loading();
    audio.play().catch(() => finish(true));
  }

  const value =
    active && index.data
      ? { index: index.data, slug, quizOnly, origin, state, toggle, stop }
      : null;
  return (
    <LessonAudioContext.Provider value={value}>
      {children}
      {active && index.isError && (
        <div className="lesson-audio-notice">
          เสียงภาษาญี่ปุ่นยังโหลดไม่ได้{" "}
          <button type="button" onClick={() => void index.refetch()}>
            ลองใหม่
          </button>
        </div>
      )}
    </LessonAudioContext.Provider>
  );
}

export function LessonAudioButton({
  kind,
  text,
  reading,
  slug,
  quiz = false,
  fallbackKind,
  hideUnavailable = false,
  showText = false,
}: {
  kind: LessonAudioKind;
  text: string;
  reading?: string;
  slug?: string;
  quiz?: boolean;
  fallbackKind?: LessonAudioKind;
  hideUnavailable?: boolean;
  showText?: boolean;
}) {
  const context = useContext(LessonAudioContext);
  const control = useId();
  const allowed = !!context && (!context.quizOnly || quiz);
  const kana = reading || (kind === "term" ? "" : undefined);
  const [resolved, setResolved] = useState<{
    lookup: string;
    keys: string[];
  }>();
  const lookup = `${kind}\x1f${fallbackKind}\x1f${text}\x1f${kana}`;
  useEffect(() => {
    if (!allowed || kana === undefined || !globalThis.crypto?.subtle) return;
    let cancelled = false;
    void Promise.all(
      (fallbackKind ? [kind, fallbackKind] : [kind]).map((type) =>
        audioLookupKey(type, text, kana),
      ),
    )
      .then((keys) => {
        if (!cancelled) setResolved({ lookup, keys });
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [allowed, fallbackKind, kind, lookup, kana, text]);
  const lesson = slug || context?.slug;
  const keys = resolved?.lookup === lookup ? resolved.keys : undefined;
  const audioId = keys
    ?.map(
      (key) =>
        (lesson ? context?.index.lessons[lesson]?.[key] : undefined) ??
        context?.index.shared[key],
    )
    .find(Boolean);
  const path = audioId && context?.index.files[audioId];
  if (!context || !allowed || !keys) return null;
  if (
    !path ||
    !/^ja\/metan-normal\/wav-[a-f0-9]{24}\/[a-f0-9]{64}\.mp3$/.test(path)
  ) {
    return hideUnavailable || kind === "term" || kind === "quiz_choice" ? null : (
      <small className="audio-unavailable">ยังไม่มีเสียง</small>
    );
  }
  const state = context.state?.control === control ? context.state.phase : null;
  const busy = state === "loading" || state === "playing";
  const label = !reading || text === reading ? text : `${text} (${reading})`;
  return (
    <span className="lesson-audio-control">
      {showText && <span lang="ja">{text}</span>}
      <button
        type="button"
        className="lesson-audio-button"
        data-active={busy || undefined}
        aria-label={`${busy ? "หยุดเสียง" : state === "error" ? "ลองฟังอีกครั้ง" : "ฟังเสียง"} ${label}`}
        onClick={() =>
          context.toggle(
            control,
            `${context.origin}/storage/v1/object/public/${bucket}/${path}`,
          )
        }
      >
        {busy ? (
          <Square size={13} aria-hidden="true" />
        ) : (
          <Volume2 size={14} aria-hidden="true" />
        )}
      </button>
      <span
        role="status"
        className={state === "error" ? "lesson-audio-error" : "sr-only"}
      >
        {state === "loading"
          ? "กำลังโหลดเสียง…"
          : state === "error"
            ? "เล่นเสียงไม่ได้ กรุณาลองอีกครั้ง"
            : ""}
      </span>
    </span>
  );
}

export function useStopAudioOnChange(scope: string | number | undefined) {
  const stop = useContext(LessonAudioContext)?.stop;
  useLayoutEffect(() => stop, [scope, stop]);
}

export function AudioText({
  text,
  slug,
  quiz,
}: {
  text: string;
  slug?: string;
  quiz?: boolean;
}) {
  const context = useContext(LessonAudioContext);
  if (!context || (context.quizOnly && !quiz)) return text;
  const segments = text.split(
    /([\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}々ー]+[。！？]?)/u,
  );
  return segments.map((part, index) =>
    index % 2 && !/^\p{Script=Han}$/u.test(part) ? (
      <span className="lesson-audio-line" key={index}>
        <span lang="ja">{part}</span>
        <LessonAudioButton kind="term" text={part} slug={slug} quiz={quiz} />
      </span>
    ) : (
      part
    ),
  );
}

export function KanjiReadingList({
  character,
  readings,
}: {
  character: string;
  readings: string[];
}) {
  return readings.length
    ? [...new Set(readings)].map((reading) => (
        <span className="lesson-audio-line" key={reading}>
          <span lang="ja">{reading}</span>
          <LessonAudioButton kind="kanji" text={character} reading={reading} />
        </span>
      ))
    : "—";
}

export function KanjiAudioReadings({
  character,
  onyomi,
  kunyomi,
  primary,
}: {
  character: string;
  onyomi: string[];
  kunyomi: string[];
  primary?: string;
}) {
  const available = useContext(LessonAudioContext);
  if (!available) return null;
  const rows = [
    ["音読み", onyomi],
    ["訓読み", kunyomi],
  ] as const;
  const groups = rows
    .map(([label, values]) => ({
      label,
      values: [...new Set(values)].filter(
        (value) =>
          !primary || normalizeReading(value) !== normalizeReading(primary),
      ),
    }))
    .filter((group) => group.values.length);
  if (!groups.length) return null;
  return (
    <details className="kanji-audio-readings">
      <summary>คำอ่านเพิ่มเติม</summary>
      <dl>
        {groups.map(({ label, values }) => (
          <div key={label}>
            <dt lang="ja">{label}</dt>
            <dd>
              <KanjiReadingList character={character} readings={values} />
            </dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
