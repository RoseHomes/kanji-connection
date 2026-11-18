import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Lesson from "./Lesson";
const mocks = vi.hoisted(() => ({ api: vi.fn(), save: vi.fn() }));
vi.mock("../api", () => ({ api: mocks.api }));
vi.mock("../auth", () => ({
  useAuth: () => ({ session: { user: { id: "developer" } }, ready: true }),
}));
vi.mock("../guest-learning", () => ({ saveGuestLesson: mocks.save }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
const lesson = {
  id: 1,
  chapter: 2,
  slug: "chapter-02",
  title_th: "Private lesson",
  status: "needs_review",
  summary_th: "",
  anchors: ["木"],
  kanjis: [],
  introduction_th: "fixture",
  provenance: "Private",
  private_development: true,
  sections: [
    {
      kind: "vocabulary",
      pdf_pages: [23],
      blocks: [
        {
          vocabulary: [
            { word: "木", reading: "き", meaning_th: "ต้นไม้", pdf_page: 23 },
          ],
        },
      ],
    },
  ],
};
function mount() {
  render(
    <MemoryRouter initialEntries={["/lessons/chapter-02"]}>
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <Routes>
          <Route path="/lessons/:slug" element={<Lesson />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}
it("renders stored lesson sections but disables progress writes in a read-only account", async () => {
  mocks.api.mockImplementation((url: string) =>
    Promise.resolve(
      url === "/health"
        ? { content_mode: "database", account_writes_enabled: false }
        : url === "/me/dashboard"
          ? { lessons: [] }
          : lesson,
    ),
  );
  mount();
  await screen.findByText("ต้นไม้");
  expect(screen.getByRole("button", { name: "บันทึกว่าอ่านจบแล้ว" })).toBeDisabled();
  expect(screen.getByText(/โหมดอ่านอย่างเดียว/)).toBeVisible();
  expect(mocks.save).not.toHaveBeenCalled();
});
it("shows a health failure and never falls back to a guest save", async () => {
  mocks.api.mockImplementation((url: string) =>
    url === "/health"
      ? Promise.reject(new Error("Network unavailable"))
      : Promise.resolve(lesson),
  );
  mount();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Network unavailable",
  );
  expect(screen.getByRole("button", { name: "บันทึกว่าอ่านจบแล้ว" })).toBeDisabled();
  expect(mocks.save).not.toHaveBeenCalled();
});
