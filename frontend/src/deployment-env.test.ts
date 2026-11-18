import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { loadEnv, resolveConfig } from "vite";
import {
  PUBLIC_BROWSER_ENV_PREFIXES,
  requireProductionConfig,
} from "./deployment-config";

const valid = {
  VITE_API_URL: "https://api.example.test",
  VITE_SUPABASE_URL: "https://auth.example.test",
  VITE_SUPABASE_PUBLISHABLE_KEY: "sb_publishable_ci_fixture",
};
const excluded = [
  "VITE_VERCEL_ENV",
  "VITE_VERCEL_URL",
  "VITE_VERCEL_GIT_COMMIT_SHA",
  "VITE_USER_NODE_ENV",
  "VITE_DATABASE_URL",
  "VITE_VERCEL_SECRET",
];
beforeEach(() => {
  for (const [name, value] of Object.entries(valid)) vi.stubEnv(name, value);
  for (const name of excluded) vi.stubEnv(name, "NEVER_EMIT_TEST_CREDENTIAL");
});
afterEach(() => vi.unstubAllEnvs());

it("reproduces the broad-prefix failure and validates the narrow public configuration", () => {
  expect(() =>
    requireProductionConfig(loadEnv("production", false, "VITE_")),
  ).toThrow(/remove other VITE_/);
  const env = loadEnv("production", false, PUBLIC_BROWSER_ENV_PREFIXES);
  expect(env).toEqual(valid);
  expect(() => requireProductionConfig(env)).not.toThrow();
});

it("excludes metadata and server variables from Vite's actual browser environment", async () => {
  const config = await resolveConfig(
    {
      configFile: false,
      envDir: false,
      envPrefix: PUBLIC_BROWSER_ENV_PREFIXES,
    },
    "build",
    "production",
  );
  for (const name of excluded) expect(config.env).not.toHaveProperty(name);
  for (const [name, value] of Object.entries(valid))
    expect(config.env[name]).toBe(value);
});

it("still rejects unexpected browser keys sharing an allowed prefix", () => {
  vi.stubEnv("VITE_API_URL_SECRET", "NEVER_EMIT_TEST_CREDENTIAL");
  expect(() =>
    requireProductionConfig(
      loadEnv("production", false, PUBLIC_BROWSER_ENV_PREFIXES),
    ),
  ).toThrow(/remove other VITE_/);
});
