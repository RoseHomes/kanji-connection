import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Home from "./Home";
const mocks = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../api", () => ({ api: mocks.api }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
function mount() {
  render(
    <MemoryRouter>
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <Home />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}
it("previews actual eligible API cards and changes the displayed reading", async () => {
  mocks.api.mockImplementation((path: string) =>
    Promise.resolve(
      path.startsWith("/kanjis")
        ? [
            {
              character: "木",
              meaning_th: "ต้นไม้",
              kunyomi: ["き"],
              onyomi: [],
              review_status: "sample",
            },
            {
              character: "森",
              meaning_th: "ป่าไม้",
              kunyomi: ["もり"],
              onyomi: [],
              review_status: "sample",
            },
          ]
        : [],
    ),
  );
  mount();
  fireEvent.click(await screen.findByRole("button", { name: "森" }));
  expect(screen.getByText("もり")).toBeVisible();
  expect(screen.getByRole("button", { name: "森" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(mocks.api.mock.calls.every((call) => call[1].anonymous === true)).toBe(
    true,
  );
});
it("shows publication empty states without fabricating lessons", async () => {
  mocks.api.mockResolvedValue([]);
  mount();
  await screen.findByRole("heading", { name: "บทเรียนสาธารณะกำลังเตรียมพร้อม" });
  expect(document.querySelectorAll(".lesson-card")).toHaveLength(0);
  expect(screen.getByRole("link", { name: /เลือกบทเรียน/ })).toHaveAttribute(
    "href",
    "/lessons",
  );
});
it("never features private or needs-review response entries", async () => {
  mocks.api.mockImplementation((path: string) =>
    Promise.resolve(
      path.startsWith("/kanjis")
        ? [
            {
              character: "林",
              meaning_th: "PRIVATE_CARD",
              review_status: "needs_review",
              kunyomi: [],
              onyomi: [],
            },
          ]
        : [
            {
              id: 1,
              chapter: 1,
              title_th: "PRIVATE_TITLE",
              slug: "private",
              anchors: [],
              status: "needs_review",
              is_available: true,
              private_development: true,
            },
          ],
    ),
  );
  mount();
  await screen.findByText("ตัวอักษรตกแต่ง · บัตรเรียนจะแสดงเมื่อมีเนื้อหาเผยแพร่");
  await waitFor(() =>
    expect(screen.queryByText("กำลังโหลดข้อมูล…")).not.toBeInTheDocument(),
  );
  expect(screen.queryByText("PRIVATE_CARD")).not.toBeInTheDocument();
  expect(screen.queryByText("PRIVATE_TITLE")).not.toBeInTheDocument();
});
