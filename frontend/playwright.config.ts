import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";
const python =
  process.platform === "win32"
    ? `"${resolve("../.venv/Scripts/python.exe")}"`
    : "python";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  use: {
    baseURL: "http://127.0.0.1:5173",
    channel: process.env.CI ? "chromium" : "msedge",
  },
  webServer: [
    {
      command: `${python} -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: "../backend",
      env: { CONTENT_SOURCE: "sample", ENABLE_USER_WRITES: "false" },
      url: "http://127.0.0.1:8000/api/v1/health",
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --port 5173 --strictPort",
      env: { VITE_SUPABASE_URL: "", VITE_SUPABASE_PUBLISHABLE_KEY: "" },
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
    },
  ],
});
