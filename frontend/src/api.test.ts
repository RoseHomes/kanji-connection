import { afterEach, expect, it, vi } from "vitest";
import { api } from "./api";
const mocks = vi.hoisted(() => ({ getSession: vi.fn() }));
vi.mock("./supabase", () => ({
  supabase: { auth: { getSession: mocks.getSession } },
}));
afterEach(() => {
  vi.resetAllMocks();
  vi.unstubAllGlobals();
});
it("public requests do not depend on or transmit a Supabase session", async () => {
  mocks.getSession.mockRejectedValue(new Error("Auth unavailable"));
  const request = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
  vi.stubGlobal("fetch", request);
  await expect(api("/kanjis", { anonymous: true })).resolves.toEqual([]);
  expect(mocks.getSession).not.toHaveBeenCalled();
  expect(request.mock.calls[0][1].headers.has("Authorization")).toBe(false);
  expect(request.mock.calls[0][1]).not.toHaveProperty("anonymous");
});
it("a stale session retries public learning reads anonymously", async () => {
  mocks.getSession.mockResolvedValue({
    data: { session: { access_token: "stale-fixture" } },
  });
  const request = vi
    .fn()
    .mockResolvedValueOnce({ ok: false, status: 401 })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ ok: true }) });
  vi.stubGlobal("fetch", request);
  await expect(api("/learning/practice/chapter-01")).resolves.toEqual({
    ok: true,
  });
  expect(request).toHaveBeenCalledTimes(2);
  expect(request.mock.calls[0][1].headers.has("Authorization")).toBe(true);
  expect(request.mock.calls[1][1].headers.has("Authorization")).toBe(false);
});
it("account requests retain bearer authentication", async () => {
  mocks.getSession.mockResolvedValue({
    data: { session: { access_token: "synthetic-fixture" } },
  });
  const request = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => ({}) });
  vi.stubGlobal("fetch", request);
  await api("/me/dashboard");
  expect(mocks.getSession).toHaveBeenCalledOnce();
  expect(
    request.mock.calls[0][1].headers
      .get("Authorization")
      ?.startsWith("Bearer "),
  ).toBe(true);
});
