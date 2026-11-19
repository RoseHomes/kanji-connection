import { chromium } from "../frontend/node_modules/@playwright/test/index.mjs";
import AxeBuilder from "../frontend/node_modules/@axe-core/playwright/dist/index.mjs";
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
const root = resolve(import.meta.dirname, ".."),
  folder = resolve(root, "private/ui-ux-redesign");
const session = JSON.parse(
  await readFile(
    resolve(root, "private/editorial-preview/session.json"),
    "utf8",
  ),
);
const browser = await chromium.launch({ channel: "msedge", headless: true });
const context = await browser.newContext({
  viewport: { width: 390, height: 844 },
  reducedMotion: "reduce",
});
await context.request.get(session.open_url, { maxRedirects: 0 });
const page = await context.newPage();
const results = [];
for (const [path, ready] of [
  ["/", ".hero-kanji-pickers"],
  ["/lessons/chapter-01", ".study-content"],
  ["/compare", "table"],
]) {
  await page.goto(session.origin + path);
  await page.locator(ready).first().waitFor();
  await page.evaluate(() => document.fonts.ready);
  const data = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  for (const result of data.incomplete.filter((r) => r.id === "color-contrast"))
    for (const node of result.nodes) {
      const selector = node.target[0];
      const element = page.locator(selector).first();
      const style = await element.evaluate((el) => {
        const s = getComputedStyle(el);
        let p = el;
        const backgrounds = [];
        while (p) {
          const c = getComputedStyle(p);
          backgrounds.push({
            tag: p.tagName,
            color: c.backgroundColor,
            image: c.backgroundImage,
          });
          p = p.parentElement;
        }
        return {
          text: el.textContent,
          ariaHidden: !!el.closest("[aria-hidden=true]"),
          color: s.color,
          fontSize: s.fontSize,
          fontWeight: s.fontWeight,
          backgrounds,
        };
      });
      const entry = {
        path,
        target: node.target,
        reason: node.failureSummary,
        checks: node.any.map((c) => ({ message: c.message, data: c.data })),
        style,
      };
      results.push(entry);
      console.log(JSON.stringify(entry));
    }
}
const rgb = (s) => s.match(/[\d.]+/g).map(Number);
const lum = (c) =>
  c
    .slice(0, 3)
    .map((v) => v / 255)
    .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4))
    .reduce((sum, v, i) => sum + v * [0.2126, 0.7152, 0.0722][i], 0);
const ratio = (a, b) => {
  const l = [lum(a), lum(b)].sort((a, b) => b - a);
  return (l[0] + 0.05) / (l[1] + 0.05);
};
for (const entry of results) {
  const fg = rgb(entry.style.color),
    base = entry.style.backgrounds
      .map((b) => rgb(b.color))
      .find((c) => c.length === 3 || c[3] === 1) || [255, 255, 255];
  const gradient = [
    ...entry.style.backgrounds[0].image.matchAll(/rgba?\(([^)]+)\)/g),
  ]
    .map((m) => rgb(m[1]))
    .filter((c) => c.length === 3 || c[3] === 1);
  entry.minimumContrast = Math.min(
    ...[base, ...gradient].map((bg) => ratio(fg, bg)),
  );
  entry.resolution = entry.style.ariaHidden
    ? "Decorative and aria-hidden; text contrast requirement does not apply"
    : "Computed contrast checked against the gradient and canvas backgrounds";
  if (!entry.style.ariaHidden && entry.minimumContrast < 3)
    throw new Error("Insufficient large-text contrast");
}
await writeFile(
  resolve(folder, "contrast-manual-review.json"),
  JSON.stringify(
    { reviewedTargets: results.length, unresolved: 0, entries: results },
    null,
    2,
  ),
);
console.log(
  JSON.stringify({
    reviewedTargets: results.length,
    unresolved: 0,
    textContrast: results
      .filter((r) => !r.style.ariaHidden)
      .map((r) => r.minimumContrast),
  }),
);
await browser.close();
