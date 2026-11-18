import { defineConfig } from "vitest/config";
import process from "node:process";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { loadEnv } from "vite";
import { requirePublicAuthConfig } from "./src/auth-config.ts";
import {
  PUBLIC_BROWSER_ENV_PREFIXES,
  requireProductionConfig,
} from "./src/deployment-config.ts";
export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, ".", PUBLIC_BROWSER_ENV_PREFIXES);
  requirePublicAuthConfig(
    env.VITE_SUPABASE_URL,
    env.VITE_SUPABASE_PUBLISHABLE_KEY,
  );
  if (
    command === "build" &&
    (mode !== "demo" || process.env.VERCEL === "1" || process.env.VERCEL_ENV)
  ) {
    requireProductionConfig(env);
  }
  return {
    // Match loadEnv so platform metadata and unrelated VITE_ values never enter
    // import.meta.env. Keep validation for all variables that can enter it.
    envPrefix: PUBLIC_BROWSER_ENV_PREFIXES,
    plugins: [react(), tailwindcss()],
    server: { proxy: { "/api": "http://127.0.0.1:8000" } },
    test: {
      include: ["src/**/*.test.{ts,tsx}"],
      environment: "jsdom",
      setupFiles: ["./src/test-setup.ts"],
    },
  };
});
