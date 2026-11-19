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
import { LazyMotion, domAnimation } from "motion/react";
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
        <LazyMotion features={domAnimation}><Home /></LazyMotion>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}
it("previews actual authorized comparison cards with clickable readings", async () => {
  mocks.api.mockImplementation((path: string) =>
    Promise.resolve(
      path.includes("comparison-groups")
        ? [
            {
              id: "wood",
              title: "木 / 森",
              chapter: 2,
              characters: [
                {
                  character: "木",
                  meaning_th: "ต้นไม้",
                  memory_note: "ลำต้นและกิ่งไม้",
                  reading: {
                    form: "木",
                    reading: "き",
                    label_th: "คำอ่านตัวอย่าง",
                  },
                },
                {
                  character: "森",
                  meaning_th: "ป่าไม้",
                  memory_note: "ต้นไม้สามต้นรวมกัน",
                  reading: {
                    form: "森",
                    reading: "もり",
                    label_th: "คำอ่านตัวอย่าง",
                  },
                },
              ],
            },
          ]
        : [],
    ),
  );
  mount();
  fireEvent.click(await screen.findByRole("button", { name: "森" }));
  await waitFor(() => expect(screen.getByText("もり")).toBeVisible());
  expect(screen.getByRole("button", { name: "森" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(
    screen.getByRole("link", { name: /ลองดูความต่างให้ชัดขึ้น/ }),
  ).toHaveAttribute("href", "/compare?group=wood");
});
it("shows honest empty states without fabricated chapters", async () => {
  mocks.api.mockResolvedValue([]);
  mount();
  await screen.findByRole("heading", { name: "บทเรียนสาธารณะกำลังเตรียมพร้อม" });
  expect(document.querySelectorAll(".lesson-card")).toHaveLength(0);
  expect(document.querySelectorAll(".hero-kanji-pickers button")).toHaveLength(
    0,
  );
});
it("uses authorized learner routes and never fetches personal records", async () => {
  mocks.api.mockResolvedValue([]);
  mount();
  await screen.findByRole("heading", { name: "บทเรียนสาธารณะกำลังเตรียมพร้อม" });
  expect(mocks.api.mock.calls.map((c) => c[0]).sort()).toEqual([
    "/learning/catalog",
    "/learning/comparison-groups",
  ]);
});
