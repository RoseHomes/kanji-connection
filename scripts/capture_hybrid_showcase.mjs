import { chromium } from "../frontend/node_modules/@playwright/test/index.mjs";
import AxeBuilder from "../frontend/node_modules/@axe-core/playwright/dist/index.mjs";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";
const root = resolve(import.meta.dirname, ".."),
  folder = resolve(root, "private/hybrid-learning"),
  shots = resolve(folder, "showcase");
await mkdir(shots, { recursive: true });
const session = JSON.parse(
  await readFile(
    resolve(root, "private/editorial-preview/session.json"),
    "utf8",
  ),
);
const reportPath = resolve(folder, "browser-verification.json"),
  report = JSON.parse(await readFile(reportPath, "utf8"));
const final = { screenshots: [], checks: [], accessibility: [] };
const browser = await chromium.launch({ channel: "msedge", headless: true });
const ensure = (x, m) => {
  if (!x) throw new Error(m);
};
async function ready(page, selector) {
  await page.locator(selector).first().waitFor();
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(250);
  ensure(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
    "Overflow " + page.url().split("?")[0],
  );
}
async function shot(page, label) {
  const path = resolve(shots, label + ".png");
  await page.screenshot({ path, animations: "disabled" });
  final.screenshots.push(path);
}
async function axe(page, label) {
  const r = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  const record = {
    label,
    violations: r.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => ({
        target: n.target,
        reason: n.failureSummary,
      })),
    })),
    incomplete: r.incomplete.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => ({
        target: n.target,
        reason: n.failureSummary,
      })),
    })),
    passes: r.passes.length,
  };
  final.accessibility.push(record);
  ensure(!record.violations.length, "Axe violation " + label);
}
try {
  for (const [name, width, height] of [
    ["desktop", 1440, 1000],
    ["tablet", 820, 1180],
    ["mobile", 390, 844],
    ["small", 320, 800],
  ]) {
    const ctx = await browser.newContext({
      viewport: { width, height },
      reducedMotion: "reduce",
      ...(width <= 390 ? { isMobile: true, hasTouch: true } : {}),
    });
    await ctx.request.get(session.open_url, { maxRedirects: 0 });
    const p = await ctx.newPage();
    await p.goto(session.origin + "/lessons/chapter-01");
    await ready(p, ".guided-stage[data-stage=discover]");
    await shot(p, name + "-entry");
    await axe(p, name + "-entry");
    await p.getByRole("button", { name: "เริ่มเรียน", exact: true }).click();
    await ready(p, ".guided-stage[data-stage=learn-1]");
    await shot(p, name + "-learn");
    await axe(p, name + "-learn");
    if (width <= 1050) {
      const trigger = p.locator(".learning-actions .action-outline");
      await trigger.click();
      await ready(p, ".chapter-outline.is-open");
      await shot(p, name + "-outline");
      await axe(p, name + "-outline");
      await p.locator(".chapter-outline button").first().focus();
      await p.keyboard.press("Escape");
      ensure(
        await trigger.evaluate((n) => n === document.activeElement),
        "Outline Escape focus",
      );
      ensure(
        (await trigger.getAttribute("aria-expanded")) === "false",
        "Outline did not dismiss",
      );
    }
    const related = p.locator(".related-learning-pairs a").first();
    await related.click();
    await ready(p, "table");
    await p
      .getByRole("link", { name: "กลับไปยังช่วงที่กำลังเรียน", exact: true })
      .click();
    await ready(p, ".guided-stage[data-stage=learn-1]");
    await p.locator(".learning-actions .review-mode-switch").click();
    await ready(p, ".full-lesson");
    ensure(
      new URL(p.url()).searchParams.get("stage") === "learn-1",
      "Persistent mode switch lost stage",
    );
    await shot(p, name + "-full");
    await axe(p, name + "-full");
    await p.locator(".learning-actions .review-mode-switch").click();
    await ready(p, ".guided-stage[data-stage=learn-1]");
    await p.goto(
      session.origin + "/lessons/chapter-01?mode=guided&stage=connect",
    );
    await ready(p, ".guided-stage[data-stage=connect]");
    await shot(p, name + "-connect");
    await p.goto(
      session.origin + "/lessons/chapter-01?mode=guided&stage=check",
    );
    await ready(p, ".checkpoint input[type=radio]");
    await shot(p, name + "-check");
    await p.getByRole("combobox", { name: "เลือกบทเรียน", exact: true }).click();
    await p.getByRole("listbox").waitFor();
    await shot(p, name + "-picker");
    await p.keyboard.press("Escape");
    for (const chapter of [27, 29]) {
      await p.goto(
        session.origin + `/lessons/chapter-${chapter}?mode=guided&stage=use`,
      );
      await ready(p, ".sentence-card");
      ensure(
        (await p.locator(".sentence-card").count()) ===
          (chapter === 27 ? 2 : 3),
        "Guided sentences missing",
      );
      await shot(p, `${name}-chapter-${chapter}-use`);
    }
    // Snapshot context is session-only and URL recovery works even if storage is unavailable.
    const blocked = await ctx.newPage();
    await blocked.addInitScript(() =>
      Object.defineProperty(window, "sessionStorage", {
        get() {
          throw new Error("Storage unavailable");
        },
      }),
    );
    await blocked.goto(
      session.origin + "/lessons/chapter-01?mode=guided&stage=learn-2",
    );
    await ready(blocked, ".guided-stage[data-stage=learn-2]");
    await blocked
      .locator(".learning-actions")
      .getByRole("button")
      .last()
      .click();
    await ready(blocked, ".guided-stage[data-stage=learn-3]");
    await blocked.reload();
    await ready(blocked, ".guided-stage[data-stage=learn-3]");
    await blocked.close();
    final.checks.push({
      viewport: name,
      persistentOutline: width <= 1050,
      persistentModeSwitch: true,
      relatedCompareReturn: true,
      guidedSentences: 5,
      blockedStorageRecovery: true,
    });
    await ctx.close();
    console.log(name + " final interaction and visual checks passed");
  }
  report.screenshots = [
    ...new Set([...report.screenshots, ...final.screenshots]),
  ];
  report.accessibility = [
    ...new Map(
      [...report.accessibility, ...final.accessibility].map((a) => [
        a.label,
        a,
      ]),
    ).values(),
  ];
  report.finalChecks = final.checks;
  report.summary.axeScans = report.accessibility.length;
  report.summary.axeViolations = report.accessibility.reduce(
    (n, a) => n + a.violations.length,
    0,
  );
  report.summary.screenshots = report.screenshots.length;
  ensure(report.summary.axeViolations === 0, "Accessibility issue remains");
  await writeFile(reportPath, JSON.stringify(report, null, 2));
  await writeFile(
    resolve(folder, "final-visual-review.json"),
    JSON.stringify(final, null, 2),
  );
  const gallery = await browser.newPage({
    viewport: { width: 1800, height: 1320 },
  });
  const cards = [
    [
      "Before · desktop long lesson",
      resolve(folder, "before/desktop-lesson.png"),
    ],
    ["After · guided entry", resolve(shots, "desktop-entry.png")],
    ["After · small Kanji group", resolve(shots, "desktop-learn.png")],
    ["After · complete review", resolve(shots, "desktop-full.png")],
    ["Before · mobile document", resolve(folder, "before/mobile-lesson.png")],
    ["After · mobile focus", resolve(shots, "mobile-learn.png")],
    ["After · accessible picker", resolve(shots, "mobile-picker.png")],
    ["After · optional quick check", resolve(shots, "mobile-check.png")],
  ];
  const tiles = await Promise.all(
    cards.map(
      async ([label, file]) =>
        `<article><h2>${label}</h2><div><img src="data:image/png;base64,${(await readFile(file)).toString("base64")}"></div></article>`,
    ),
  );
  await gallery.setContent(
    `<style>*{box-sizing:border-box}body{background:#f8f5ef;color:#253448;font-family:Arial;padding:30px;margin:0}h1{margin:0;font-size:29px}p{color:#58657a;margin:12px 0 24px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}article{background:white;border:1px solid #e6ddd1;border-radius:16px;overflow:hidden}h2{font-size:16px;margin:0;padding:13px}article div{height:510px;overflow:hidden;border-top:1px solid #e6ddd1}img{display:block;width:100%}</style><h1>Kanji Connection · Hybrid Learning</h1><p>Actual protected preview · 30 chapters · Guided + Full Lesson · Click-only controls · Desktop, tablet, 390px and 320px verified</p><div class="grid">${tiles.join("")}</div>`,
  );
  await gallery
    .locator("img")
    .evaluateAll((imgs) => Promise.all(imgs.map((i) => i.decode())));
  await gallery.screenshot({
    path: resolve(folder, "before-after-contact-sheet.png"),
    fullPage: true,
  });
  console.log(JSON.stringify(report.summary));
} catch (e) {
  final.failure = e.message;
  await writeFile(
    resolve(folder, "final-visual-review.json"),
    JSON.stringify(final, null, 2),
  );
  console.error(e.stack);
  process.exitCode = 1;
} finally {
  await browser.close();
}
