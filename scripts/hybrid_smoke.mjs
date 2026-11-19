import { chromium } from "../frontend/node_modules/@playwright/test/index.mjs";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
const root = resolve(import.meta.dirname, ".."),
  folder = resolve(root, "private/hybrid-learning");
await mkdir(resolve(folder, "screenshots"), { recursive: true });
const s = JSON.parse(
  await readFile(
    resolve(root, "private/editorial-preview/session.json"),
    "utf8",
  ),
);
const browser = await chromium.launch({ channel: "msedge", headless: true });
const errors = [];
for (const [name, width, height] of [
  ["desktop", 1440, 1000],
  ["tablet", 820, 1180],
  ["mobile", 390, 844],
  ["small", 320, 800],
]) {
  const ctx = await browser.newContext({
    viewport: { width, height },
    reducedMotion: "reduce",
  });
  await ctx.request.get(s.open_url, { maxRedirects: 0 });
  const p = await ctx.newPage();
  p.on("pageerror", (e) => errors.push(e.message));
  await p.goto(s.origin + "/lessons/chapter-01");
  await p.locator(".guided-stage").waitFor();
  await p.evaluate(() => document.fonts.ready);
  await p.screenshot({
    path: resolve(folder, "screenshots", name + "-entry.png"),
    fullPage: true,
  });
  console.log(
    name,
    await p.locator(".study-content").count(),
    p.url().split("?")[1],
  );
  await p.getByRole("button", { name: "เริ่มเรียนทีละกลุ่ม", exact: true }).click();
  await p.locator(".study-content").first().waitFor();
  await p.screenshot({
    path: resolve(folder, "screenshots", name + "-learn.png"),
    fullPage: true,
  });
  await p.getByRole("button", { name: "ดูบทเรียนทั้งหมด", exact: true }).click();
  await p.locator(".full-lesson").waitFor();
  await p.screenshot({
    path: resolve(folder, "screenshots", name + "-full.png"),
    fullPage: true,
  });
  const overflow = await p.evaluate(() => ({
    viewport: innerWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  console.log(name, overflow);
  await ctx.close();
}
await browser.close();
await writeFile(
  resolve(folder, "smoke.json"),
  JSON.stringify({ errors }, null, 2),
);
console.log(JSON.stringify({ errors }));
