import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Review from "./pages/Review";
import Catalog from "./pages/Catalog";
import Quiz from "./pages/Quiz";
const mocks = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("./api", () => ({ api: mocks.api }));
vi.mock("./auth", () => ({
  useAuth: () => ({ session: null, ready: true, configured: true }),
}));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
function mount(child: React.ReactNode) {
  render(
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
it.each([Dashboard, Review])(
  "explains personal access without requesting protected records",
  (Page) => {
    mount(<Page />);
    expect(
      screen.getByRole("link", { name: /เรียนโดยไม่เข้าสู่ระบบ/ }),
    ).toHaveAttribute("href", "/lessons");
    expect(screen.getByRole("link", { name: "เข้าสู่ระบบ" })).toBeTruthy();
    expect(mocks.api).not.toHaveBeenCalled();
  },
);
it("shows a public catalog empty state without offering signin as an editorial bypass", async () => {
  mocks.api.mockResolvedValue([]);
  mount(<Catalog />);
  await screen.findByRole("heading", { name: "บทเรียนสาธารณะกำลังเตรียมพร้อม" });
  expect(
    screen.queryByRole("link", { name: /เข้าสู่ระบบ/ }),
  ).not.toBeInTheDocument();
  expect(mocks.api.mock.calls[0][0]).toBe("/learning/catalog");
});
it("opens public practice without requesting personal records", async () => {
  mocks.api.mockImplementation((path: string) =>
    Promise.resolve(
      path === "/health"
        ? { content_mode: "database", account_writes_enabled: false }
        : [],
    ),
  );
  mount(<Quiz />);
  await screen.findByRole("heading", { name: "แบบฝึกหัดกำลังเตรียมพร้อม" });
  expect(
    mocks.api.mock.calls.every((call) => !call[0].startsWith("/me/")),
  ).toBe(true);
});
