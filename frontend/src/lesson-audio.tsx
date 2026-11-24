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

export type LessonAudioKind = "kanji" | "component" | "word" | "sentence";
const attribution = "VOICEVOX:四国めたん";
const bucket = "kanji-japanese-audio";
const indexPath = "/japanese-audio/index.json";
const timeoutMs = 12_000;

interface PlaybackIndex {
  version: number;
  bucket: string;
  attribution: string;
  lessons: Record<string, Record<string, string>>;
  files: Record<string, string>;
}

async function getIndex() {
  const response = await fetch(indexPath);
  if (!response.ok) return null;
  const index = (await response.json()) as PlaybackIndex;
  if (
    index.version !== 1 ||
    index.bucket !== bucket ||
    index.attribution !== attribution
  )
    return null;
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
  entries: Record<string, string>;
  files: Record<string, string>;
  origin: string;
  state: PlaybackState;
  toggle: (control: string, url: string) => void;
}
const LessonAudioContext = createContext<AudioContextValue | null>(null);

export function LessonAudio({
  slug,
  enabled,
  playbackScope,
  children,
}: {
  slug: string;
  enabled: boolean;
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

  useLayoutEffect(() => {
    setState(null);
    return release;
  }, [active, playbackScope, release, slug]);

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

  const entries = active && index.data?.lessons?.[slug];
  const value =
    entries && index.data?.files
      ? { entries, files: index.data.files, origin, state, toggle }
      : null;
  return (
    <LessonAudioContext.Provider value={value}>
      {children}
      {value && <small className="lesson-audio-credit">{attribution}</small>}
    </LessonAudioContext.Provider>
  );
}

export function LessonAudioButton({
  kind,
  text,
  reading,
}: {
  kind: LessonAudioKind;
  text: string;
  reading?: string;
}) {
  const context = useContext(LessonAudioContext);
  const control = useId();
  const entries = context?.entries;
  const [resolved, setResolved] = useState<{ lookup: string; key: string }>();
  const lookup = `${kind}\x1f${text}\x1f${reading}`;
  useEffect(() => {
    if (!entries || !reading || !globalThis.crypto?.subtle) return;
    let cancelled = false;
    void audioLookupKey(kind, text, reading)
      .then((key) => {
        if (!cancelled) setResolved({ lookup, key });
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [entries, kind, lookup, reading, text]);
  const audioId =
    resolved?.lookup === lookup ? entries?.[resolved.key] : undefined;
  const path = audioId && context?.files[audioId];
  if (
    !context ||
    !path ||
    !/^ja\/metan-normal\/wav-[a-f0-9]{24}\/[a-f0-9]{64}\.mp3$/.test(path)
  )
    return null;
  const state = context.state?.control === control ? context.state.phase : null;
  const busy = state === "loading" || state === "playing";
  const label = text === reading ? text : `${text} (${reading})`;
  return (
    <span className="lesson-audio-control">
      <button
        type="button"
        className="lesson-audio-button"
        aria-label={`${busy ? "หยุดเสียง" : state === "error" ? "ลองฟังอีกครั้ง" : "ฟังเสียง"} ${label}`}
        onClick={() =>
          context.toggle(
            control,
            `${context.origin}/storage/v1/object/public/${bucket}/${path}`,
          )
        }
      >
        {busy ? (
          <Square size={15} aria-hidden="true" />
        ) : (
          <Volume2 size={17} aria-hidden="true" />
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
              {values.map((reading) => (
                <span className="lesson-audio-line" key={reading}>
                  <span lang="ja">{reading}</span>
                  <LessonAudioButton
                    kind="kanji"
                    text={character}
                    reading={reading}
                  />
                </span>
              ))}
            </dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
