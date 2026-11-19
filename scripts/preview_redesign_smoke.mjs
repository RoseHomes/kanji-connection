import { chromium } from "../frontend/node_modules/@playwright/test/index.mjs";
import { readFile, mkdir, writeFile } from "node:fs/promises";
const session = JSON.parse(
  await readFile(
    new URL("../private/editorial-preview/session.json", import.meta.url),
    "utf8",
  ),
);
const folder = new URL("../private/ui-ux-redesign/", import.meta.url);
await mkdir(folder, { recursive: true });
console.log("Launching browser");
const browser = await chromium.launch({
  channel: "msedge",
  headless: true,
  timeout: 30000,
});
console.log("Browser launched");
const mobile = process.argv.includes("--mobile");
const context = await browser.newContext({
  viewport: mobile
    ? { width: 390, height: 844 }
    : { width: 1440, height: 1000 },
});
await context.request.get(session.open_url, {
  maxRedirects: 0,
  timeout: 15000,
});
console.log("Preview authorized");
const page = await context.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
for (const [name, path, selector] of [
  ["home", "/", ".hero-kanji-pickers"],
  ["lesson", "/lessons/chapter-01", ".study-content"],
  ["compare", "/compare", "table"],
  ["quiz", "/quiz/chapter-01", "input[type=radio]"],
  ["detail", "/explore/人", ".kanji-detail-header"],
]) {
  await page.goto(session.origin + path);
  await page.locator(selector).first().waitFor({ timeout: 45000 });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({
    path: new URL(
      name + (mobile ? "-mobile" : "-desktop") + ".png",
      folder,
    ).pathname.replace(/^\/(\w:)/, "$1"),
    fullPage: true,
  });
  console.log(
    JSON.stringify({
      name,
      overflow: await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      text: (await page.locator("h1").innerText()).slice(0, 80),
    }),
  );
}
console.log(JSON.stringify({ errors }));
await writeFile(
  new URL("smoke.json", folder),
  JSON.stringify({ errors }, null, 2),
);
await browser.close();
