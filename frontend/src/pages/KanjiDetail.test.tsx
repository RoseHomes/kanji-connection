import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import KanjiDetail from "./KanjiDetail";
const mocks = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../api", () => ({ api: mocks.api }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
it("loads public readings, vocabulary and relationships without personal APIs", async () => {
  mocks.api.mockImplementation((path: string) =>
    Promise.resolve(
      path.includes("/vocabulary")
        ? [
            {
              id: 1,
              written_form: "木",
              reading: "き",
              meaning_th: "ต้นไม้",
              usage_notes: "",
            },
          ]
        : path.includes("/relations")
          ? { related: ["林"], relations: [] }
          : {
              character: "木",
              meaning_th: "ต้นไม้",
              kunyomi: ["き"],
              onyomi: ["モク"],
              strokes: 4,
              component: "木",
              note_th: "",
              source_url: "",
              review_status: "published",
            },
    ),
  );
  render(
    <MemoryRouter initialEntries={["/explore/木"]}>
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <Routes>
          <Route path="/explore/:character" element={<KanjiDetail />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
  await screen.findByRole("heading", { name: "ต้นไม้" });
  await screen.findByRole("link", { name: "林" });
  expect(document.querySelector("ruby rt")).toHaveTextContent("き");
  expect(
    mocks.api.mock.calls.every(
      (call) => call[1].anonymous === true && !call[0].startsWith("/me/"),
    ),
  ).toBe(true);
});
