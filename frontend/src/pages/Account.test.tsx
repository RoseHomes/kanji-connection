import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Account from "./Account";
const mocks = vi.hoisted(() => ({
  signInWithPassword: vi.fn(),
  signUp: vi.fn(),
  signOut: vi.fn(),
  session: false,
}));
vi.mock("../supabase", () => ({ supabase: { auth: mocks } }));
vi.mock("../auth", () => ({
  useAuth: () => ({
    session: mocks.session ? { user: { email: "reader@example.test" } } : null,
    ready: true,
    configured: true,
  }),
}));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  mocks.session = false;
});
it("offers signup with email confirmation and password signin", async () => {
  mocks.signUp.mockResolvedValue({ data: { session: null }, error: null });
  render(
    <MemoryRouter>
      <Account />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole("button", { name: "ยังไม่มีบัญชี · สมัครสมาชิก" }));
  fireEvent.change(screen.getByLabelText("อีเมล"), {
    target: { value: "reader@example.test" },
  });
  fireEvent.change(screen.getByLabelText("รหัสผ่าน"), {
    target: { value: "long-password" },
  });
  fireEvent.click(screen.getByRole("button", { name: "สมัครสมาชิก" }));
  await screen.findByText("กรุณาตรวจอีเมลเพื่อยืนยันบัญชี แล้วกลับมาเข้าสู่ระบบ");
  expect(mocks.signUp.mock.calls[0][0].email).toBe("reader@example.test");
  fireEvent.click(screen.getByRole("button", { name: "มีบัญชีแล้ว · เข้าสู่ระบบ" }));
  mocks.signInWithPassword.mockResolvedValue({
    data: { session: null },
    error: { message: "error" },
  });
  fireEvent.change(screen.getByLabelText("รหัสผ่าน"), {
    target: { value: "long-password" },
  });
  fireEvent.click(screen.getByRole("button", { name: "เข้าสู่ระบบ" }));
  await waitFor(() =>
    expect(mocks.signInWithPassword).toHaveBeenCalledTimes(1),
  );
});
it("signs out the current browser session", async () => {
  mocks.session = true;
  mocks.signOut.mockResolvedValue({ error: null });
  render(
    <MemoryRouter>
      <Account />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole("button", { name: "ออกจากระบบ" }));
  await waitFor(() =>
    expect(mocks.signOut).toHaveBeenCalledWith({ scope: "local" }),
  );
});
