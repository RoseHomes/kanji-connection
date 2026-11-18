import { defineConfig } from "vitest/config";
import process from "node:process";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { loadEnv } from "vite";
import { requirePublicAuthConfig } from "./src/auth-config.ts";
import { requireProductionConfig } from "./src/deployment-config.ts";
export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, ".", "VITE_");
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
    plugins: [react(), tailwindcss()],
    server: { proxy: { "/api": "http://127.0.0.1:8000" } },
    test: {
      include: ["src/**/*.test.{ts,tsx}"],
      environment: "jsdom",
      setupFiles: ["./src/test-setup.ts"],
    },
  };
});
