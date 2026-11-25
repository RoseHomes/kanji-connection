import { webcrypto } from "node:crypto";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { domAnimation, LazyMotion } from "motion/react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import {
  audioLookupKey,
  LessonAudio,
  KanjiReadingList,
  type LessonAudioKind,
} from "./lesson-audio";
import { LessonExperience } from "./lesson-experience";
import { PracticeRound } from "./pages/Quiz";
import type { PracticeQuestion } from "./presentation-types";
import type { LessonDetail } from "./types";

vi.mock("./auth", () => ({ useAuth: () => ({ session: null }) }));
vi.mock("./api", () => ({
  api: vi.fn(async (path: string) =>
    path.endsWith("/check")
      ? {
          correct: true,
          correct_option_id: "a",
          correct_text: "やま",
          explanation: "山 อ่านว่า やま",
          selection_explanation: "",
          persisted: false,
        }
      : path.includes("/practice/")
        ? [
            {
              id: "test-reading",
              kind: "reading",
              prompt: "คำว่า「山」อ่านอย่างไร?",
              options: [
                { id: "a", text: "やま" },
                { id: "b", text: "さん" },
              ],
            },
          ]
        : path.includes("/lesson/")
          ? lesson
          : [],
  ),
}));

const lesson: LessonDetail = {
  id: 1,
  chapter: 1,
  slug: "chapter-01",
  part: 1,
  is_available: true,
  status: "published",
  title_th: "ตัวอย่าง",
  summary_th: "สังเกตรูป",
  introduction_th: "สังเกตรูป",
  anchors: ["山"],
  available_count: 1,
  provenance: "",
  kanjis: [
    {
      character: "山",
      meaning_th: "ภูเขา",
      onyomi: ["サン"],
      kunyomi: ["やま"],
      strokes: 3,
      romaji: "",
      component: "",
      note_th: "",
      source_url: "",
      review_status: "published",
    },
  ],
  sections: [
    {
      kind: "cards",
      blocks: [
        {
          cards: [
            {
              character: "山",
              reading_example: "やま",
              example: "",
              meaning_th: "ภูเขา",
              memory_note: "",
              study: {
                schema_version: 2,
                role: "core",
                required: true,
                reading: {
                  kind: "character",
                  form: "山",
                  reading: "やま",
                  label_th: "คำอ่านตัวอย่าง",
                  note_th: "",
                },
                example: {
                  word: "山に行く",
                  reading: "やまにいく",
                  target_scope: "วลี",
                  role: "core_phrase",
                  optional: false,
                },
                scope_note_th: "",
                mnemonic_note_th: "",
              },
            },
          ],
        },
      ],
    },
    {
      kind: "vocabulary",
      blocks: [
        {
          vocabulary: [{ word: "山", reading: "やま", meaning_th: "ภูเขา" }],
          sentences: [
            {
              text: "山に行きます。",
              reading: "やまにいきます。",
              meaning_th: "ไปภูเขา",
              note_th: "",
              source_url: "",
            },
          ],
        },
      ],
    },
  ],
};

class TestAudio {
  static instances: TestAudio[] = [];
  onplaying: (() => void) | null = null;
  onerror: (() => void) | null = null;
  pause = vi.fn();
  removeAttribute = vi.fn();
  load = vi.fn();
  play = vi.fn(async () => {});
  constructor(public url: string) {
    TestAudio.instances.push(this);
  }
}

async function mount(
  stage: string,
  htmlFirst = false,
  quizQuestion?: PracticeQuestion,
) {
  vi.stubGlobal("crypto", webcrypto);
  vi.stubGlobal("Audio", TestAudio);
  vi.stubEnv("VITE_SUPABASE_URL", "https://kanjitest.supabase.co");
  const entries: [LessonAudioKind, string, string, string][] = [
    ["kanji", "山", "やま", "a"],
    ["kanji", "山", "さん", "b"],
    ["word", "山", "やま", "a"],
    ["word", "山に行く", "やまにいく", "c"],
    ["sentence", "山に行きます。", "やまにいきます。", "d"],
    ["quiz_choice", "やま", "やま", "a"],
    ["quiz_choice", "さん", "さん", "b"],
  ];
  const files: Record<string, string> = {};
  const keys: Record<string, string> = {};
  for (const [kind, text, reading, seed] of entries) {
    const id = `wav-${seed.repeat(24)}`;
    files[id] = `ja/metan-normal/${id}/${seed.repeat(64)}.mp3`;
    keys[await audioLookupKey(kind, text, reading)] = id;
  }
  let requests = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      htmlFirst && requests++ === 0
        ? new Response("<html></html>", {
            headers: { "content-type": "text/html" },
          })
        : {
            ok: true,
            headers: new Headers({ "content-type": "application/json" }),
            json: async () => ({
              version: 2,
              bucket: "kanji-japanese-audio",
              attribution: "VOICEVOX:四国めたん",
              lessons: { "chapter-01": keys },
              shared: keys,
              files,
            }),
          },
    ),
  );
  function OpenCheckpoint() {
    const navigate = useNavigate();
    return (
      <button onClick={() => navigate("?mode=guided&stage=check")}>
        checkpoint test
      </button>
    );
  }
  if (stage === "shared") {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <LessonAudio enabled playbackScope="explorer">
          <KanjiReadingList character="山" readings={["やま", "サン", "や"]} />
        </LessonAudio>
      </QueryClientProvider>,
    );
    return;
  }
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter
        initialEntries={[`/lessons/chapter-01?mode=guided&stage=${stage}`]}
      >
        <LazyMotion features={domAnimation}>
          {quizQuestion ? (
            <LessonAudio enabled playbackScope="quiz">
              <PracticeRound questions={[quizQuestion]} slug={lesson.slug} />
            </LessonAudio>
          ) : (
            <>
              <OpenCheckpoint />
              <LessonExperience lesson={lesson} catalog={[]} />
            </>
          )}
        </LazyMotion>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
  TestAudio.instances = [];
  sessionStorage.clear();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

it("resolves exact readings without a lesson and labels missing readings without substituting", async () => {
  await mount("shared");
  fireEvent.click(
    await screen.findByRole("button", { name: "ฟังเสียง 山 (やま)" }),
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "ฟังเสียง 山 (サン)" }),
  );
  expect(TestAudio.instances[0].url).not.toBe(TestAudio.instances[1].url);
  expect(await screen.findByText("ยังไม่มีเสียง")).toBeVisible();
  expect(screen.queryByRole("button", { name: "ฟังเสียง 山 (や)" })).toBeNull();
});

it("surfaces an SPA HTML fallback and recovers when the index becomes available", async () => {
  await mount("shared", true);
  await screen.findByText("เสียงภาษาญี่ปุ่นยังโหลดไม่ได้");
  expect(screen.queryByRole("button", { name: /ฟังเสียง/ })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "ลองใหม่" }));
  expect(
    await screen.findByRole("button", { name: "ฟังเสียง 山 (やま)" }),
  ).toBeVisible();
  expect(fetch).toHaveBeenCalledWith("/assets/japanese-audio-index.json");
});

it("reveals word and choice sounds only after server-confirmed reading feedback", async () => {
  await mount("check");
  fireEvent.click(await screen.findByRole("radio", { name: /やま/ }));
  expect(screen.queryByRole("button", { name: /ฟังเสียง/ })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: /ตรวจคำตอบ/ }));
  expect(
    await screen.findByRole("button", { name: "ฟังเสียง 山 (やま)" }),
  ).toBeVisible();
  expect(
    await screen.findByRole("button", { name: "ฟังเสียง さん" }),
  ).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: /ดูผลการฝึก/ }));
  fireEvent.click(await screen.findByRole("button", { name: /ดูคำตอบทั้งรอบ/ }));
  fireEvent.click(screen.getByRole("button", { name: "ดูรายละเอียด ข้อ 1" }));
  expect(
    await screen.findByRole("button", { name: "ฟังเสียง さん" }),
  ).toBeVisible();
});

const meaningQuestion: PracticeQuestion = {
  id: "test-meaning",
  kind: "meaning",
  prompt: "「山」มีความหมายใดตามที่เรียนในบทนี้?",
  options: [
    { id: "a", text: "ภูเขา" },
    { id: "b", text: "แม่น้ำ" },
  ],
};

it("plays the published lesson reading before a Thai meaning answer and replays it in results", async () => {
  await mount("quiz", false, meaningQuestion);
  const promptAudio = await screen.findByRole("button", {
    name: "ฟังเสียง 山 (やま)",
  });
  fireEvent.click(promptAudio);
  expect(TestAudio.instances[0].url).toContain("wav-" + "a".repeat(24));
  fireEvent.click(screen.getByRole("radio", { name: /ภูเขา/ }));
  fireEvent.click(screen.getByRole("button", { name: /ตรวจคำตอบ/ }));
  fireEvent.click(await screen.findByRole("button", { name: /ดูผลการฝึก/ }));
  fireEvent.click(await screen.findByRole("button", { name: /ดูคำตอบทั้งรอบ/ }));
  fireEvent.click(screen.getByRole("button", { name: "ดูรายละเอียด ข้อ 1" }));
  expect(
    await screen.findByRole("button", { name: "ฟังเสียง 山 (やま)" }),
  ).toBeVisible();
});

it("withholds potentially revealing meaning and shape audio until feedback", async () => {
  await mount("quiz", false, {
    ...meaningQuestion,
    options: [
      { id: "a", text: "ภูเขา (やま)" },
      { id: "b", text: "แม่น้ำ" },
    ],
  });
  expect(screen.queryByRole("button", { name: /ฟังเสียง/ })).toBeNull();
  fireEvent.click(screen.getByRole("radio", { name: /ภูเขา/ }));
  fireEvent.click(screen.getByRole("button", { name: /ตรวจคำตอบ/ }));
  expect(
    await screen.findByRole("button", { name: "ฟังเสียง 山 (やま)" }),
  ).toBeVisible();
  cleanup();
  await mount("quiz", false, {
    ...meaningQuestion,
    kind: "shape",
    prompt: "ข้อใดอธิบายจุดต่างของรูป「山 / 川」ได้ถูกต้อง?",
  });
  expect(screen.queryByRole("button", { name: /ฟังเสียง/ })).toBeNull();
  fireEvent.click(screen.getByRole("radio", { name: /ภูเขา/ }));
  fireEvent.click(screen.getByRole("button", { name: /ตรวจคำตอบ/ }));
  expect(
    await screen.findByRole("button", { name: "ฟังเสียง 山 (やま)" }),
  ).toBeVisible();
  expect(screen.queryByRole("button", { name: /ฟังเสียง 川/ })).toBeNull();
});

it("plays a kanji, reading alternatives and phrases in Guided Learning, then reuses the URL in Full Lesson", async () => {
  await mount("learn-1");
  const reading = await screen.findByRole("button", {
    name: "ฟังเสียง 山 (やま)",
  });
  expect(
    await screen.findByRole("button", { name: "ฟังเสียง 山に行く (やまにいく)" }),
  ).toBeVisible();
  fireEvent.click(screen.getByText("คำอ่านเพิ่มเติม"));
  expect(
    await screen.findByRole("button", { name: "ฟังเสียง 山 (サン)" }),
  ).toBeVisible();
  fireEvent.click(reading);
  expect(screen.getByText("กำลังโหลดเสียง…")).toBeInTheDocument();
  const first = TestAudio.instances[0];
  act(() => first.onplaying?.());
  fireEvent.click(screen.getByRole("button", { name: "ดูบทเรียนทั้งหมด" }));
  expect(first.pause).toHaveBeenCalled();
  const summary = document.querySelector("[data-card-summary]") as HTMLElement;
  fireEvent.click(
    await within(summary).findByRole("button", { name: "ฟังเสียง 山 (やま)" }),
  );
  expect(TestAudio.instances[1].url).toBe(first.url);
});

it("cancels rapid repeated clicks, allows retry after error, and stops playback on the reading checkpoint", async () => {
  await mount("use");
  const word = await screen.findByRole("button", { name: "ฟังเสียง 山 (やま)" });
  fireEvent.click(word);
  fireEvent.click(word);
  expect(TestAudio.instances).toHaveLength(1);
  expect(TestAudio.instances[0].pause).toHaveBeenCalled();
  fireEvent.click(word);
  fireEvent.click(
    await screen.findByRole("button", { name: /ฟังเสียง 山に行きます/ }),
  );
  expect(TestAudio.instances[1].pause).toHaveBeenCalled();
  act(() => TestAudio.instances[2].onerror?.());
  expect(screen.getByText("เล่นเสียงไม่ได้ กรุณาลองอีกครั้ง")).toBeVisible();
  fireEvent.click(
    screen.getByRole("button", { name: /ลองฟังอีกครั้ง 山に行きます/ }),
  );
  act(() => TestAudio.instances[3].onplaying?.());
  fireEvent.click(screen.getByRole("button", { name: "checkpoint test" }));
  expect(await screen.findByRole("radio", { name: /やま/ })).toBeVisible();
  expect(TestAudio.instances[3].pause).toHaveBeenCalled();
  expect(
    screen.queryByRole("button", { name: /ฟังเสียง|หยุดเสียง/ }),
  ).not.toBeInTheDocument();
});

it("groups ruby and the translation before the shared audio action and keeps status in the row", async () => {
  await mount("use");
  const button = await screen.findByRole("button", { name: /ฟังเสียง 山に行きます/ });
  const row = button.parentElement!;
  const copy = row.firstElementChild!;
  expect(row).toHaveClass("lesson-audio-row");
  expect(copy).toHaveClass("lesson-audio-copy");
  expect(copy.querySelector("ruby rt")).toHaveTextContent("やまにいきます。");
  expect(copy).toHaveTextContent("ไปภูเขา");
  expect(copy.nextElementSibling).toBe(button);
  fireEvent.click(button);
  expect(within(row).getByRole("status")).toHaveTextContent("กำลังโหลดเสียง");
  act(() => TestAudio.instances[0].onerror?.());
  expect(within(row).getByRole("status")).toHaveTextContent("เล่นเสียงไม่ได้");
});
