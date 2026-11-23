import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  act,
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
  resetPasswordForEmail: vi.fn(),
  updateUser: vi.fn(),
  session: false,
  recovering: false,
  finishPasswordRecovery: vi.fn(),
}));
vi.mock("../supabase", () => ({ supabase: { auth: mocks } }));
vi.mock("../auth", () => ({
  useAuth: () => ({
    session: mocks.session
      ? { user: { id: "reader", email: "reader-account@example.test" } }
      : null,
    ready: true,
    configured: true,
    recoveringPassword: mocks.recovering,
    finishPasswordRecovery: mocks.finishPasswordRecovery,
  }),
}));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  mocks.session = false;
  mocks.recovering = false;
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
  await screen.findByText(/หากอีเมลนี้ใช้สมัครได้/);
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

it("passes fresh Turnstile tokens to login, signup and reset and clears expired tokens", async () => {
  vi.stubEnv("VITE_TURNSTILE_SITE_KEY", "public-test-key");
  let callbacks: {
    callback: (token: string) => void;
    "expired-callback": () => void;
  };
  const renderWidget = vi.fn(
    (_container: HTMLElement, options: typeof callbacks) => {
      callbacks = options;
      return "widget";
    },
  );
  const remove = vi.fn();
  vi.stubGlobal("turnstile", { render: renderWidget, remove });
  mocks.signInWithPassword.mockResolvedValue({
    data: { session: null },
    error: { status: 429 },
  });
  mocks.signUp.mockResolvedValue({
    data: { session: null },
    error: { code: "user_already_exists" },
  });
  mocks.resetPasswordForEmail.mockResolvedValue({
    error: { status: 429, code: "over_email_send_rate_limit" },
  });
  render(
    <MemoryRouter>
      <Account />
    </MemoryRouter>,
  );
  await waitFor(() => expect(renderWidget).toHaveBeenCalled());
  fireEvent.change(screen.getByLabelText("อีเมล"), {
    target: { value: "reader@example.test" },
  });
  const login = screen.getByRole("button", { name: "เข้าสู่ระบบ" });
  expect(login).toBeDisabled();
  act(() => callbacks.callback("expired-token"));
  expect(login).toBeEnabled();
  act(() => callbacks["expired-callback"]());
  expect(login).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "เริ่มการตรวจสอบใหม่" }));
  await waitFor(() => expect(renderWidget).toHaveBeenCalledTimes(2));
  act(() => callbacks.callback("login-token"));
  fireEvent.change(screen.getByLabelText("รหัสผ่าน"), {
    target: { value: "legacy8!" },
  });
  fireEvent.click(login);
  await screen.findByText(/ส่งคำขอบ่อยเกินไป/);
  expect(mocks.signInWithPassword).toHaveBeenCalledWith(
    expect.objectContaining({ options: { captchaToken: "login-token" } }),
  );
  expect(login).toBeDisabled();

  fireEvent.click(screen.getByRole("button", { name: "ยังไม่มีบัญชี · สมัครสมาชิก" }));
  await waitFor(() => expect(renderWidget).toHaveBeenCalledTimes(4));
  act(() => callbacks.callback("signup-token"));
  fireEvent.change(screen.getByLabelText("รหัสผ่าน"), {
    target: { value: "reader@example.test" },
  });
  fireEvent.click(screen.getByRole("button", { name: "สมัครสมาชิก" }));
  await screen.findByText(/รหัสผ่านต้องไม่ตรง/);
  expect(mocks.signUp).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("รหัสผ่าน"), {
    target: { value: "mountain-river-42" },
  });
  fireEvent.click(screen.getByRole("button", { name: "สมัครสมาชิก" }));
  await screen.findByText(/หากอีเมลนี้ใช้สมัครได้/);
  expect(mocks.signUp).toHaveBeenCalledWith(
    expect.objectContaining({
      options: expect.objectContaining({ captchaToken: "signup-token" }),
    }),
  );

  fireEvent.click(screen.getByRole("button", { name: "มีบัญชีแล้ว · เข้าสู่ระบบ" }));
  fireEvent.click(screen.getByRole("button", { name: "ลืมรหัสผ่าน?" }));
  await screen.findByText(/โปรดทำการตรวจสอบความปลอดภัย/);
  act(() => callbacks.callback("reset-token"));
  fireEvent.click(screen.getByRole("button", { name: "ส่งลิงก์ตั้งรหัสผ่านใหม่" }));
  await screen.findByText(/หากมีบัญชีที่ใช้อีเมลนี้/);
  expect(mocks.resetPasswordForEmail).toHaveBeenCalledWith(
    "reader@example.test",
    {
      redirectTo: `${window.location.origin}/account`,
      captchaToken: "reset-token",
    },
  );
  expect(remove).toHaveBeenCalled();
});

it.each([false, true])(
  "validates the new password before calling Supabase (recovery: %s)",
  async (recovering) => {
    mocks.session = true;
    mocks.recovering = recovering;
    mocks.updateUser.mockResolvedValue({ error: null });
    render(
      <MemoryRouter>
        <Account />
      </MemoryRouter>,
    );
    if (!recovering) {
      fireEvent.click(screen.getByRole("button", { name: "เปลี่ยนรหัสผ่าน" }));
      fireEvent.change(screen.getByLabelText("รหัสผ่านปัจจุบัน"), {
        target: { value: "old-password" },
      });
    } else {
      expect(screen.queryByLabelText("รหัสผ่านปัจจุบัน")).toBeNull();
    }
    const input = screen.getByLabelText("รหัสผ่านใหม่");
    const submit = screen.getByRole("button", { name: "บันทึกรหัสผ่านใหม่" });
    for (const weak of [
      "short",
      "READER-ACCOUNT",
      "password1234",
      "abcabcabcabc",
    ]) {
      fireEvent.change(input, { target: { value: weak } });
      fireEvent.click(submit);
      expect(mocks.updateUser).not.toHaveBeenCalled();
    }
    fireEvent.change(input, { target: { value: "blue-mountains-47" } });
    fireEvent.click(submit);
    await screen.findByText("บันทึกรหัสผ่านใหม่แล้ว");
    expect(mocks.updateUser).toHaveBeenCalledWith({
      password: "blue-mountains-47",
      ...(recovering ? {} : { current_password: "old-password" }),
    });
  },
);
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
