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
it("uses account-scoped catalog metadata, preserves private labels and clears an empty filter", async () => {
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
  await screen.findByText("ส่วนตัว · รอตรวจ");
  expect(screen.getByText(/ส่วนตัวสำหรับพัฒนา/)).toBeVisible();
  expect(mocks.api.mock.calls[0][0]).toContain("/learning/catalog");
  fireEvent.change(screen.getByRole("textbox", { name: "ค้นหาบทเรียน" }), {
    target: { value: "missing" },
  });
  await screen.findByText("ไม่พบบทเรียนที่ตรงกับคำค้น");
  fireEvent.click(screen.getByRole("button", { name: "ล้างตัวกรอง" }));
  await screen.findByRole("heading", { name: "ต้นไม้" });
});
it("paginates explorer results beyond the first 30 teaching cards", async () => {
  mocks.api.mockImplementation((url: string) =>
    Promise.resolve(
      url.includes("offset=30")
        ? [{ ...card, character: "林" }]
        : Array.from({ length: 31 }, (_, i) => ({
            ...card,
            character: String.fromCharCode(0x4e00 + i),
          })),
    ),
  );
  mount(<Explorer />);
  await waitFor(() => expect(screen.getAllByRole("article")).toHaveLength(30));
  fireEvent.click(screen.getByRole("button", { name: "ถัดไป" }));
  await waitFor(() => expect(screen.getAllByRole("article")).toHaveLength(1));
  expect(screen.getByText("หน้า 2")).toBeVisible();
  expect(screen.getByRole("button", { name: "ถัดไป" })).toBeDisabled();
});
it("accepts a new comparison pair without showing the unrelated tree explanation", async () => {
  mocks.api.mockResolvedValue([card, { ...card, character: "林" }]);
  mount(<Compare />);
  await screen.findByRole("textbox", { name: "ตัวอักษรที่ต้องการเปรียบเทียบ" });
  fireEvent.change(
    screen.getByRole("textbox", { name: "ตัวอักษรที่ต้องการเปรียบเทียบ" }),
    { target: { value: "火,水" } },
  );
  fireEvent.click(screen.getByRole("button", { name: "เปรียบเทียบ" }));
  await waitFor(() =>
    expect(
      mocks.api.mock.calls.some((c) =>
        c[0].includes(encodeURIComponent("火,水")),
      ),
    ).toBe(true),
  );
  expect(screen.queryByText("ส่วนประกอบร่วมที่ระบุในข้อมูล")).not.toBeInTheDocument();
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
