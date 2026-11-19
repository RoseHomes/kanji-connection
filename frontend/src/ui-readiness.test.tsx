import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DataState } from "./components";
import Catalog from "./pages/Catalog";
import Explorer from "./pages/Explorer";
import Compare from "./pages/Compare";
import Review from "./pages/Review";
import type { Kanji } from "./types";

const mocks = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("./api", () => ({ api: mocks.api }));
vi.mock("./auth", () => ({
  useAuth: () => ({ session: { user: { id: "developer" } }, ready: true }),
}));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  localStorage.clear();
});
function mount(child: React.ReactNode) {
  return render(
    <MemoryRouter>
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        {child}
      </QueryClientProvider>
    </MemoryRouter>,
  );
}
const card: Kanji = {
  character: "木",
  meaning_th: "ต้นไม้",
  onyomi: [],
  kunyomi: ["き"],
  romaji: "ki",
  strokes: 4,
  component: "",
  note_th: "",
  source_url: "",
  review_status: "needs_review",
};

it("shows an actionable error even while a dependent query remains pending", () => {
  mount(
    <DataState
      loading={true}
      error={new Error("Connection unavailable")}
      retry={() => {}}
    />,
  );
  expect(screen.getByRole("alert")).toHaveTextContent("Connection unavailable");
  expect(screen.queryByText("กำลังโหลดข้อมูล…")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "ดูบทเรียนที่เข้าถึงได้" })).toHaveAttribute(
    "href",
    "/lessons",
  );
  expect(screen.queryByText(/8000/)).not.toBeInTheDocument();
});
it("uses the authorized catalog and clears an empty category without exposing review status", async () => {
  mocks.api.mockImplementation((url: string) =>
    Promise.resolve(
      url.includes("q=missing")
        ? []
        : [
            {
              id: 1,
              chapter: 2,
              slug: "chapter-02",
              part: 1,
              title_th: "ต้นไม้",
              summary_th: "fixture",
              anchors: ["木"],
              status: "needs_review",
              is_available: true,
              private_development: true,
              available_count: 14,
            },
          ],
    ),
  );
  mount(<Catalog />);
  await screen.findByRole("heading", { name: "ต้นไม้" });
  expect(screen.queryByText(/รอตรวจ/)).not.toBeInTheDocument();
  expect(mocks.api.mock.calls[0][0]).toContain("/learning/catalog");
  fireEvent.click(screen.getByRole("button", { name: "ทบทวน" }));
  await screen.findByText("ยังไม่มีบทในกลุ่มนี้");
  fireEvent.click(screen.getByRole("button", { name: "ดูทุกหมวด" }));
  await screen.findByRole("heading", { name: "ต้นไม้" });
});
it("paginates explorer results beyond the first 30 teaching cards", async () => {
  mocks.api.mockImplementation((url: string) =>
    Promise.resolve(
      url.includes("catalog")
        ? []
        : url.includes("offset=30")
          ? [{ ...card, character: "林" }]
          : Array.from({ length: 31 }, (_, i) => ({
              ...card,
              character: String.fromCharCode(0x4e00 + i),
            })),
    ),
  );
  mount(<Explorer />);
  await waitFor(() =>
    expect(document.querySelectorAll(".explorer-tile")).toHaveLength(30),
  );
  fireEvent.click(screen.getByRole("button", { name: /สำรวจชุดถัดไป/ }));
  await waitFor(() =>
    expect(document.querySelectorAll(".explorer-tile")).toHaveLength(1),
  );
  expect(screen.getByRole("button", { name: /สำรวจชุดถัดไป/ })).toBeDisabled();
});
it("switches curated comparison groups with zero text entry", async () => {
  const character = (g: string) => ({
    character: g,
    meaning_th: g,
    memory_note: "reviewed cue",
    reading: { form: g, reading: "き", label_th: "คำอ่านตัวอย่าง" },
    example: null,
  });
  mocks.api.mockResolvedValue([
    {
      id: "wood",
      chapter: 2,
      slug: "chapter-02",
      title: "木 / 林",
      category: "รูปพื้นฐาน",
      difference_th: "ไม้หนึ่งต้นและสองต้น",
      characters: [character("木"), character("林")],
    },
    {
      id: "fire",
      chapter: 4,
      slug: "chapter-04",
      title: "火 / 水",
      category: "รูปพื้นฐาน",
      difference_th: "REVIEWED_FIRE_WATER",
      characters: [character("火"), character("水")],
    },
  ]);
  mount(<Compare />);
  fireEvent.click(await screen.findByRole("button", { name: /火 \/ 水/ }));
  await screen.findByText("REVIEWED_FIRE_WATER");
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  expect(screen.queryByText("ไม้หนึ่งต้นและสองต้น")).not.toBeInTheDocument();
  expect(screen.getByRole("table")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "ส่วนประกอบ" }));
  await screen.findByText("ยังไม่มีชุดในหมวดนี้");
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "ดูชุดทั้งหมด" }));
  await screen.findByRole("table");
});

it("does not display all Kanji when an explorer category has no chapters", async () => {
  mocks.api.mockImplementation((path: string) =>
    Promise.resolve(
      path.includes("catalog")
        ? [{ chapter: 2, slug: "chapter-02", title_th: "ต้นไม้" }]
        : [card],
    ),
  );
  mount(<Explorer />);
  await waitFor(() =>
    expect(document.querySelectorAll(".explorer-tile")).toHaveLength(1),
  );
  fireEvent.click(screen.getByRole("button", { name: "ทบทวน" }));
  await screen.findByText("ยังไม่พบตัวอักษรในชุดนี้");
  expect(document.querySelectorAll(".explorer-tile")).toHaveLength(0);
});

it("resolves a category chosen before the chapter catalog finishes loading", async () => {
  let finish: (value: unknown) => void = () => {};
  const pending = new Promise((resolve) => {
    finish = resolve;
  });
  mocks.api.mockImplementation((path: string) =>
    path.includes("catalog")
      ? pending
      : Promise.resolve(
          path.includes("/learning/lesson/")
            ? { kanjis: [{ ...card, character: "林" }] }
            : [card],
        ),
  );
  mount(<Explorer />);
  fireEvent.click(screen.getByRole("button", { name: "รูปพื้นฐาน" }));
  finish([{ chapter: 2, slug: "chapter-02", title_th: "ต้นไม้" }]);
  await waitFor(() =>
    expect(
      mocks.api.mock.calls.some(
        (call) => call[0] === "/learning/lesson/chapter-02",
      ),
    ).toBe(true),
  );
  await waitFor(() =>
    expect(document.querySelector(".explorer-glyph")).toHaveTextContent("林"),
  );
});
it("does not call an empty flashcard collection a completed review", async () => {
  mocks.api.mockImplementation((url: string) =>
    Promise.resolve(
      url === "/health"
        ? { content_mode: "database", account_writes_enabled: false }
        : [],
    ),
  );
  mount(<Review />);
  await screen.findByRole("heading", { name: "ยังไม่มีบัตรคันจิที่เปิดให้เข้าถึง" });
  expect(screen.queryByText("ทบทวนครบแล้ว 🌱")).not.toBeInTheDocument();
  expect(screen.getByText(/โหมดอ่านอย่างเดียว/)).toBeVisible();
});
it("allows a flashcard reveal while disabling read-only review writes", async () => {
  mocks.api.mockImplementation((url: string) =>
    Promise.resolve(
      url === "/health"
        ? { content_mode: "database", account_writes_enabled: false }
        : [{ ...card, schedule: null, private_development: true }],
    ),
  );
  mount(<Review />);
  fireEvent.click(await screen.findByRole("button", { name: "เปิดคำตอบ" }));
  expect(screen.getByRole("button", { name: "จำได้แล้ว ✓" })).toBeDisabled();
  expect(screen.getByRole("heading", { name: "ต้นไม้" })).toBeVisible();
  expect(
    mocks.api.mock.calls.every(
      (call) => !call[1]?.method || call[1].method === "GET",
    ),
  ).toBe(true);
});
