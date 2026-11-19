import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { LazyMotion, domAnimation } from "motion/react";
import { LessonExperience } from "./lesson-experience";
import type { LessonDetail } from "./types";
const mock = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("./api", () => ({ api: mock.api }));
const lesson = {
  slug: "chapter-02",
  chapter: 2,
  title_th: "ต้นไม้",
  introduction_th: "สังเกตรูป",
  summary_th: "เริ่มรู้จัก",
  anchors: ["木", "林", "森"],
  kanjis: [
    {
      character: "木",
      meaning_th: "ต้นไม้",
      kunyomi: ["き"],
      onyomi: [],
      note_th: "ภาพต้นไม้",
      review_status: "sample",
      strokes: 4,
      source_url: "",
    },
    {
      character: "林",
      meaning_th: "หมู่ต้นไม้",
      kunyomi: ["はやし"],
      onyomi: [],
      note_th: "ไม้สองต้น",
      review_status: "sample",
      strokes: 8,
      source_url: "",
    },
    {
      character: "森",
      meaning_th: "ป่าไม้",
      kunyomi: ["もり"],
      onyomi: [],
      note_th: "ไม้สามต้น",
      review_status: "sample",
      strokes: 12,
      source_url: "",
    },
  ],
  sections: [],
} as unknown as LessonDetail;
function History() {
  const nav = useNavigate(),
    location = useLocation();
  return (
    <>
      <output data-testid="location">
        {location.pathname + location.search + location.hash}
      </output>
      <button onClick={() => nav(-1)}>test back</button>
      <button onClick={() => nav(1)}>test forward</button>
    </>
  );
}
function mount(path = "/lessons/chapter-02") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <LazyMotion features={domAnimation}>
          <History />
          <Routes>
            <Route
              path="/lessons/:slug"
              element={<LessonExperience lesson={lesson} catalog={[]} />}
            />
          </Routes>
        </LazyMotion>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}
afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.resetAllMocks();
});
it("defaults to a compact overview and navigates using previous, next and browser history", async () => {
  mock.api.mockResolvedValue([]);
  mount();
  await screen.findByRole("heading", { name: "เริ่มจากสิ่งที่ควรสังเกต" });
  expect(document.querySelectorAll(".study-content")).toHaveLength(0);
  fireEvent.click(screen.getByRole("button", { name: "เริ่มเรียน" }));
  await waitFor(() =>
    expect(screen.getByTestId("location")).toHaveTextContent("stage=learn-1"),
  );
  await waitFor(() =>
    expect(document.querySelectorAll(".kanji-card")).toHaveLength(3),
  );
  fireEvent.click(screen.getByRole("button", { name: "test back" }));
  await waitFor(() =>
    expect(screen.getByTestId("location")).toHaveTextContent("stage=discover"),
  );
  fireEvent.click(screen.getByRole("button", { name: "test forward" }));
  await waitFor(() =>
    expect(screen.getByTestId("location")).toHaveTextContent("stage=learn-1"),
  );
});
it("switches modes at the same stage and exposes all compact summaries", async () => {
  mock.api.mockResolvedValue([]);
  mount("/lessons/chapter-02?mode=guided&stage=learn-1");
  fireEvent.click(screen.getByRole("button", { name: "ดูบทเรียนทั้งหมด" }));
  await waitFor(() =>
    expect(screen.getByTestId("location")).toHaveTextContent(
      "mode=full&stage=learn-1",
    ),
  );
  expect(document.querySelectorAll("[data-card-summary]")).toHaveLength(3);
  fireEvent.click(screen.getByRole("button", { name: "เรียนเป็นช่วง" }));
  await waitFor(() =>
    expect(screen.getByTestId("location")).toHaveTextContent(
      "mode=guided&stage=learn-1",
    ),
  );
});
it("restores session position and recovers removed or invalid segments", async () => {
  mock.api.mockResolvedValue([]);
  sessionStorage.setItem(
    "kanji:lesson-position:v1:chapter-02",
    JSON.stringify({
      mode: "guided",
      stage: "learn-1",
      visited: ["discover", "learn-1"],
    }),
  );
  mount();
  await waitFor(() =>
    expect(screen.getByTestId("location")).toHaveTextContent("stage=learn-1"),
  );
  cleanup();
  mount("/lessons/chapter-02?mode=guided&stage=learn-999");
  await waitFor(() =>
    expect(screen.getByTestId("location")).toHaveTextContent("stage=learn-1"),
  );
});
it("keeps a skipped checkpoint optional and submits no answer or account writes", async () => {
  mock.api.mockResolvedValue([]);
  mount("/lessons/chapter-02?mode=guided&stage=check");
  fireEvent.click(screen.getByRole("button", { name: /ข้าม \/ ไปทวนต่อ/ }));
  await waitFor(() =>
    expect(screen.getByTestId("location")).toHaveTextContent("stage=review"),
  );
  expect(mock.api.mock.calls.every((c) => !c[1]?.method)).toBe(true);
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
});
