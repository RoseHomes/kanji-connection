import { expect, it } from "vitest";
import { requireProductionConfig } from "./deployment-config";

const valid = {
  VITE_API_URL: "https://api.example.test",
  VITE_SUPABASE_URL: "https://auth.example.test",
  VITE_SUPABASE_PUBLISHABLE_KEY: "sb_publishable_ci_fixture",
};
it("accepts the direct-HTTPS API architecture without adding an API path", () => {
  expect(() => requireProductionConfig(valid)).not.toThrow();
});
it.each([
  undefined,
  "",
  "http://localhost:8000",
  "https://localhost",
  "https://api.example.test/",
  "https://api.example.test/api/v1",
  "https://u:p@api.example.test",
  "https://YOUR_BACKEND_PROJECT.vercel.app",
])("rejects a missing or unsafe production API origin", (url) => {
  expect(() =>
    requireProductionConfig({ ...valid, VITE_API_URL: url }),
  ).toThrow(/VITE_API_URL/);
});
it("requires public Supabase configuration and never echoes a rejected secret", () => {
  const secret = "sb_secret_never_echo_this";
  try {
    requireProductionConfig({
      ...valid,
      VITE_SUPABASE_PUBLISHABLE_KEY: secret,
    });
    throw new Error("Expected rejection");
  } catch (error) {
    expect(String(error)).toContain("public publishable/anon");
    expect(String(error)).not.toContain(secret);
  }
  expect(() =>
    requireProductionConfig({ ...valid, VITE_SUPABASE_URL: undefined }),
  ).toThrow();
});
it("rejects unknown browser variables instead of bundling server credentials", () => {
  expect(() =>
    requireProductionConfig({ ...valid, VITE_DATABASE_URL: "private-fixture" }),
  ).toThrow(/remove other VITE_/);
});
