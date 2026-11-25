import { defineConfig } from "@playwright/test";

// Temporary verification config: reuse the already-running local servers.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  use: {
    baseURL: "http://127.0.0.1:5173",
    channel: "msedge",
  },
});
