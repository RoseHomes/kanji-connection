import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "./auth";
const mocks = vi.hoisted(() => ({
  listener: null as
    null | ((event: string, session: { user: { id: string } } | null) => void),
  unsubscribe: vi.fn(),
  getSession: vi.fn(),
}));
vi.mock("./supabase", () => ({
  supabase: {
    auth: {
      getSession: mocks.getSession,
      onAuthStateChange: (listener: typeof mocks.listener) => {
        mocks.listener = listener;
        return { data: { subscription: { unsubscribe: mocks.unsubscribe } } };
      },
    },
  },
}));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  mocks.listener = null;
});
function Subject() {
  const { session, ready } = useAuth();
  return <span>{ready ? session?.user.id || "guest" : "loading"}</span>;
}
it("restores a session, preserves same-owner cache on refresh, and clears it on signout", async () => {
  mocks.getSession.mockResolvedValue({
    data: { session: { user: { id: "a" } } },
    error: null,
  });
  const client = new QueryClient();
  const view = render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <Subject />
      </AuthProvider>
    </QueryClientProvider>,
  );
  await screen.findByText("a");
  client.setQueryData(["private"], { owner: "a" });
  act(() => mocks.listener?.("TOKEN_REFRESHED", { user: { id: "a" } }));
  expect(client.getQueryData(["private"])).toEqual({ owner: "a" });
  act(() => mocks.listener?.("SIGNED_OUT", null));
  expect(screen.getByText("guest")).toBeInTheDocument();
  expect(client.getQueryData(["private"])).toBeUndefined();
  view.unmount();
  expect(mocks.unsubscribe).toHaveBeenCalled();
});
it("does not overwrite a newer auth event with a delayed initial session", async () => {
  let finish: (value: unknown) => void = () => {};
  mocks.getSession.mockReturnValue(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthProvider>
        <Subject />
      </AuthProvider>
    </QueryClientProvider>,
  );
  act(() => mocks.listener?.("SIGNED_IN", { user: { id: "b" } }));
  await act(async () =>
    finish({ data: { session: { user: { id: "a" } } }, error: null }),
  );
  expect(screen.getByText("b")).toBeInTheDocument();
});
