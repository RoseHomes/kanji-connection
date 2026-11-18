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
import Dashboard from "./Dashboard";
const mocks = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../api", () => ({ api: mocks.api }));
vi.mock("../auth", () => ({
  useAuth: () => ({
    session: { user: { id: "owner" } },
    ready: true,
    configured: true,
  }),
}));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  localStorage.clear();
});
it("disables guest synchronization when account writes are unavailable", async () => {
  mocks.api.mockImplementation((path: string) =>
    Promise.resolve(
      path === "/health"
        ? { content_mode: "database", account_writes_enabled: false }
        : path === "/me/dashboard"
          ? {
              lessons: [],
              cards: {},
              due_count: 0,
              quiz: { graded: 0, correct: 0, pending: 0, recent: [] },
            }
          : [],
    ),
  );
  render(
    <MemoryRouter>
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <Dashboard />
      </QueryClientProvider>
    </MemoryRouter>,
  );
  await screen.findByText(/โหมดอ่านอย่างเดียว/);
  const button = screen.getByRole("button", { name: "ตรวจข้อมูลก่อนซิงก์" });
  expect(button).toBeDisabled();
  fireEvent.click(button);
  expect(
    mocks.api.mock.calls.every((call) => call[0] !== "/me/sync/preview"),
  ).toBe(true);
});
it("requires explicit conflict decisions before applying a guest sync", async () => {
  mocks.api.mockImplementation((path: string) => {
    if (path === "/health")
      return Promise.resolve({
        content_mode: "database",
        account_writes_enabled: true,
      });
    if (path === "/me/dashboard")
      return Promise.resolve({
        lessons: [],
        cards: {},
        due_count: 0,
        quiz: { graded: 0, correct: 0, pending: 0, recent: [] },
      });
    if (path === "/learning/lessons") return Promise.resolve([]);
    if (path === "/me/sync/preview")
      return Promise.resolve({
        snapshot: "snapshot",
        rows: [
          {
            key: "review:木",
            kind: "review",
            guest: { reviews: 4 },
            cloud: { reviews: 2 },
          },
        ],
        unavailable: [],
      });
    return Promise.resolve({ synced: true });
  });
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={cache}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  const previewButton = screen.getByRole("button", { name: "ตรวจข้อมูลก่อนซิงก์" });
  await waitFor(() => expect(previewButton).toBeEnabled());
  fireEvent.click(previewButton);
  const confirm = await screen.findByRole("button", {
    name: "ยืนยันตัวเลือกและซิงก์",
  });
  expect(confirm).toBeDisabled();
  fireEvent.click(screen.getByRole("radio", { name: "เก็บข้อมูลบัญชี" }));
  expect(confirm).toBeEnabled();
  fireEvent.click(confirm);
  await waitFor(() =>
    expect(mocks.api.mock.calls.some((c) => c[0] === "/me/sync/apply")).toBe(
      true,
    ),
  );
  const call = mocks.api.mock.calls.find((c) => c[0] === "/me/sync/apply")!;
  expect(JSON.parse(call[1].body).choices).toEqual({ "review:木": "cloud" });
  await screen.findByText("ซิงก์สำเร็จ · ยังคงเก็บสำเนาผู้เยี่ยมชมไว้ในเครื่อง");
});
