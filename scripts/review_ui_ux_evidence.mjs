// Recheck repaired findings, inspect every chapter's final reflow, and package screenshots.
import { chromium } from "../frontend/node_modules/@playwright/test/index.mjs";
import AxeBuilder from "../frontend/node_modules/@axe-core/playwright/dist/index.mjs";
import { readFile, writeFile, copyFile } from "node:fs/promises";
import { resolve } from "node:path";
const componentStyle = ".site-header,.mobile-nav{visibility:hidden!important}";
const root = resolve(import.meta.dirname, ".."),
  folder = resolve(root, "private/ui-ux-redesign"),
  shots = resolve(folder, "screenshots");
const session = JSON.parse(
  await readFile(
    resolve(root, "private/editorial-preview/session.json"),
    "utf8",
  ),
);
const reportPath = resolve(folder, "browser-verification.json");
await copyFile(
  reportPath,
  resolve(folder, "browser-full-flow-first-pass.json"),
);
const report = JSON.parse(await readFile(reportPath, "utf8"));
const browser = await chromium.launch({ channel: "msedge", headless: true });
const check = (ok, why) => {
  if (!ok) throw new Error(why);
};
const final = process.argv.includes("--resume")
  ? JSON.parse(
      await readFile(resolve(folder, "final-visual-review.json"), "utf8"),
    )
  : {
      layoutChecks: [],
      pngWidths: [],
      accessibility: [],
      normalMotion: {},
      keyboard: {},
      screenshots: [],
    };
delete final.failure;
for (const result of final.accessibility) {
  const at = report.accessibility.findIndex((r) => r.label === result.label);
  if (at >= 0) report.accessibility[at] = result;
  else report.accessibility.push(result);
}
const source = JSON.parse(
  await readFile(
    resolve(root, "private/learning-presentation/mcq-presentation-v1.json"),
    "utf8",
  ),
);
async function clean(page, selector, label) {
  await page.locator(selector).first().waitFor({ timeout: 30000 });
  await page.evaluate(() => document.fonts.ready);
  const overflow = await page
    .locator(
      ".page,.comparison-layout,.group-directory,.comparison-workspace,table,.lesson-grid,.quiz-shell",
    )
    .evaluateAll((nodes) =>
      nodes
        .filter((n) => {
          const r = n.getBoundingClientRect();
          return r.width > innerWidth + 1 || r.right > innerWidth + 1;
        })
        .map((n) => n.className),
    );
  check(!overflow.length, `Clipped overflow ${label}: ${overflow}`);
  check(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
    "Page overflow " + label,
  );
  final.layoutChecks.push(label);
}
async function axe(page, label) {
  const data = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  const result = {
    label,
    violations: data.violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      nodes: v.nodes.map((n) => ({
        target: n.target,
        summary: n.failureSummary,
      })),
    })),
    incomplete: data.incomplete.map((v) => ({
      id: v.id,
      nodes: v.nodes.length,
    })),
    passes: data.passes.length,
  };
  final.accessibility.push(result);
  const at = report.accessibility.findIndex((r) => r.label === label);
  if (at >= 0) report.accessibility[at] = result;
  else report.accessibility.push(result);
  check(
    result.violations.length === 0,
    "Accessibility regression " +
      label +
      ": " +
      result.violations.map((v) => v.id),
  );
}
try {
  for (const [name, width, height] of [
    ["desktop", 1440, 1000],
    ["tablet", 820, 1180],
    ["mobile", 390, 844],
  ]) {
    if (
      !process.argv.includes("--refresh-screenshots") &&
      new Set(
        final.layoutChecks.filter((c) => c.startsWith(name + "-chapter-")),
      ).size === 30 &&
      ["home", "detail", "compare-triad"].every((s) =>
        final.accessibility.some(
          (a) => a.label === name + "-" + s && a.violations.length === 0,
        ),
      )
    ) {
      console.log(
        `${name}: retaining all 30 final layout passes and repaired accessibility checks`,
      );
      continue;
    }
    const context = await browser.newContext({
      viewport: { width, height },
      reducedMotion: "reduce",
    });
    await context.request.get(session.open_url, { maxRedirects: 0 });
    const page = await context.newPage();
    for (let chapter = 1; chapter <= 30; chapter++) {
      const slug = `chapter-${String(chapter).padStart(2, "0")}`;
      await page.goto(session.origin + "/lessons/" + slug);
      await clean(page, ".study-content", `${name}-${slug}`);
      if (process.argv.includes("--refresh-screenshots"))
        await page.screenshot({
          path: resolve(shots, `${name}-${slug}.png`),
          fullPage: true,
        });
    }
    for (const [label, path, selector] of [
      ["home", "/", ".hero-kanji-pickers"],
      ["detail", "/explore/人", ".kanji-detail-header"],
      ["compare-triad", "/compare", "table"],
    ]) {
      await page.goto(session.origin + path);
      await clean(page, selector, `${name}-${label}`);
      await axe(page, `${name}-${label}`);
      const file = resolve(shots, `${name}-${label}.png`);
      await page.screenshot({ path: file, fullPage: true });
      if (name === "mobile" && label === "compare-triad") {
        await page.locator(".comparison-workspace").scrollIntoViewIfNeeded();
        await page.evaluate(() =>
          document
            .querySelector(".comparison-workspace")
            .scrollIntoView({ block: "start" }),
        );
        const feature = resolve(shots, "mobile-comparison-viewport.png");
        await page.screenshot({ path: feature });
        final.screenshots.push(feature);
        const table = resolve(shots, "mobile-comparison-table.png");
        await page
          .locator(".comparison-table")
          .screenshot({ path: table, style: componentStyle });
        final.screenshots.push(table);
      }
    }
    if (name === "mobile") {
      await page.getByRole("button", { name: "大 / 太", exact: true }).click();
      check(
        (await page.locator(".table-glyph").allTextContents()).join(",") ===
          "大,太",
        "Pair focus",
      );
      await page
        .getByRole("button", { name: "ส่วนประกอบ", exact: true })
        .click();
      await clean(page, "table", "mobile-comparison-category");
    }
    if (process.argv.includes("--refresh-screenshots")) {
      await page.goto(session.origin + "/quiz/chapter-01");
      await clean(page, "input[type=radio]", name + "-refreshed-quiz");
      const qs = source.chapters[0].objective_questions;
      for (let i = 0; i < qs.length; i++) {
        const q = qs[i],
          choice =
            i === 0
              ? q.options.find((o) => o.id !== q.correct_option_id).id
              : q.correct_option_id;
        await page.locator(`input[value="${choice}"]`).check();
        await page.getByRole("button", { name: /ตรวจคำตอบ/ }).click();
        await page.locator(".answer-feedback").waitFor();
        if (i === 0) {
          await page.screenshot({
            path: resolve(shots, name + "-quiz-feedback.png"),
            fullPage: true,
          });
          if (name === "mobile") {
            const file = resolve(shots, "mobile-question-panel.png");
            await page
              .locator(".question-panel")
              .screenshot({ path: file, style: componentStyle });
            final.screenshots.push(file);
          }
        }
        await page
          .getByRole("button", {
            name: i === 14 ? "ดูผลการฝึก" : "ข้อต่อไป",
            exact: true,
          })
          .click();
        if (i < 14)
          await page
            .getByRole("heading", { name: qs[i + 1].prompt, exact: true })
            .waitFor();
      }
      await clean(page, ".results-panel", name + "-refreshed-results");
      await page
        .getByRole("button", { name: "ดูคำตอบทั้งรอบ", exact: true })
        .click();
      await page.screenshot({
        path: resolve(shots, name + "-quiz-results.png"),
        fullPage: true,
      });
      if (name === "mobile") {
        const file = resolve(shots, "mobile-results-panel.png");
        await page
          .locator(".results-panel")
          .screenshot({ path: file, style: componentStyle });
        final.screenshots.push(file);
      }
    }
    await context.close();
    console.log(
      `${name}: all 30 final reflow checks and repaired findings passed`,
    );
  }
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    reducedMotion: "no-preference",
  });
  await context.request.get(session.open_url, { maxRedirects: 0 });
  const page = await context.newPage();
  await page.goto(session.origin + "/");
  await clean(page, ".hero-kanji-pickers", "normal-home");
  await page.locator(".skip").focus();
  check(
    await page
      .locator(".skip")
      .evaluate((n) => getComputedStyle(n).clipPath === "none"),
    "Skip link cannot be revealed",
  );
  await page.locator("main").focus();
  check(
    await page
      .locator(".skip")
      .evaluate((n) => getComputedStyle(n).clipPath !== "none"),
    "Skip link remains visible",
  );
  final.keyboard.skipLink = true;
  await page.getByRole("link", { name: "เริ่มเรียน", exact: true }).hover();
  await page.waitForTimeout(200);
  const before = await page
    .getByRole("link", { name: "เริ่มเรียน", exact: true })
    .evaluate((n) => getComputedStyle(n).transform);
  await page.mouse.down();
  await page.waitForTimeout(160);
  const pressed = await page
    .getByRole("link", { name: "เริ่มเรียน", exact: true })
    .evaluate((n) => getComputedStyle(n).transform);
  await page.mouse.move(0, 0);
  await page.mouse.up();
  check(before !== pressed, "Button press microinteraction missing");
  final.normalMotion = {
    reducedMotion: false,
    hoverTransform: before,
    pressTransform: pressed,
    lazyFeatures: true,
  };
  await page.goto(session.origin + "/quiz/chapter-01");
  await clean(page, "input[type=radio]", "normal-quiz");
  const questions = source.chapters[0].objective_questions;
  for (let i = 0; i < questions.length; i++) {
    const q = questions[i];
    await page.locator(`input[value="${q.correct_option_id}"]`).check();
    await page.getByRole("button", { name: /ตรวจคำตอบ/ }).click();
    await page.locator(".answer-feedback").waitFor();
    if (i === 0) {
      await page.waitForTimeout(250);
      check(
        await page
          .locator(".answer-feedback")
          .evaluate((n) => n === document.activeElement),
        "Feedback focus missing",
      );
      await axe(page, "normal-quiz-feedback");
      final.keyboard.feedbackFocus = true;
    }
    await page
      .getByRole("button", {
        name: i === 14 ? "ดูผลการฝึก" : "ข้อต่อไป",
        exact: true,
      })
      .click();
    if (i < 14) {
      await page
        .getByRole("heading", { name: questions[i + 1].prompt, exact: true })
        .waitFor();
      if (i === 0) {
        await page.waitForTimeout(260);
        check(
          await page
            .locator(".question-panel h2")
            .evaluate((n) => n === document.activeElement),
          "Next heading focus missing",
        );
        final.keyboard.nextHeadingFocus = true;
      }
    }
  }
  await clean(page, ".results-panel", "normal-quiz-results");
  await page.waitForTimeout(300);
  check(
    await page
      .locator(".results-panel h2")
      .evaluate((n) => n === document.activeElement),
    "Results focus missing",
  );
  final.keyboard.resultsFocus = true;
  await axe(page, "normal-quiz-results");
  await page.screenshot({
    path: resolve(shots, "normal-quiz-results.png"),
    fullPage: true,
  });
  final.screenshots.push(resolve(shots, "normal-quiz-results.png"));
  await context.close();
  const uniqueScreens = [
    ...new Set([...report.screenshots, ...final.screenshots]),
  ];
  for (const path of uniqueScreens) {
    const data = await readFile(path);
    const width = data.readUInt32BE(16);
    const file = path.split(/[\\/]/).pop();
    const expected =
      file.startsWith("desktop") ||
      file.startsWith("normal") ||
      file.startsWith("zoom")
        ? 1440
        : file.startsWith("tablet")
          ? 820
          : 390;
    check(
      /-(panel|table)\.png$/.test(file)
        ? width > 0 && width <= expected
        : width === expected,
      "Full-page image contains overflow: " + file + " width " + width,
    );
    final.pngWidths.push({ file, width });
  }
  report.resolvedFindings = [
    {
      issue: "Account sidebar text contrast",
      resolution: "Darker coral text verified at all three viewports",
    },
    {
      issue: "Kanji relation links below minimum touch target size",
      resolution:
        "54px tiles, WCAG 2.2 target-size scans passing at all viewports",
    },
    {
      issue: "Mobile comparison selector intrinsic width",
      resolution:
        "Constrained grid minimum width, final bounding-box and PNG-width checks pass",
    },
  ];
  report.accessibility = [
    ...new Map(report.accessibility.map((r) => [r.label, r])).values(),
  ];
  report.screenshots = uniqueScreens;
  final.layoutChecks = [...new Set(final.layoutChecks)];
  final.pngWidths = [
    ...new Map(final.pngWidths.map((v) => [v.file, v])).values(),
  ];
  final.accessibility = [
    ...new Map(final.accessibility.map((v) => [v.label, v])).values(),
  ];
  report.summary = {
    chapters: report.chapters.length,
    completedQuestionInteractions: report.chapters.reduce(
      (n, c) => n + c.questions + (c.wrongOnlyRetry ? 1 : 0),
      0,
    ),
    accessibilityViolations: report.accessibility.reduce(
      (n, r) => n + r.violations.length,
      0,
    ),
    accessibilityScans: report.accessibility.length,
    screenshots: uniqueScreens.length,
    finalReflowChecks: final.layoutChecks.length,
  };
  check(
    report.summary.accessibilityViolations === 0,
    "Unresolved accessibility finding",
  );
  check(report.chapters.length === 90, "Missing chapter flows");
  await writeFile(reportPath, JSON.stringify(report, null, 2));
  await writeFile(
    resolve(folder, "final-visual-review.json"),
    JSON.stringify(final, null, 2),
  );
  const tiles = [
    ["Desktop home", "desktop-home.png"],
    ["Lesson one", "desktop-chapter-01.png"],
    ["Click-only comparison", "desktop-compare-triad.png"],
    ["Quiz feedback", "desktop-quiz-feedback.png"],
    ["Mobile home", "mobile-home.png"],
    ["Mobile comparison", "mobile-comparison-table.png"],
    ["Mobile quiz", "mobile-question-panel.png"],
    ["Results and review", "mobile-results-panel.png"],
  ];
  const html = await Promise.all(
    tiles.map(
      async ([label, file]) =>
        `<article><h2>${label}</h2><div><img src="data:image/png;base64,${(await readFile(resolve(shots, file))).toString("base64")}"></div></article>`,
    ),
  );
  const gallery = await browser.newPage({
    viewport: { width: 1800, height: 1320 },
  });
  await gallery.setContent(
    `<style>*{box-sizing:border-box}body{margin:0;background:#f8f5ef;color:#253448;font-family:Arial;padding:35px}h1{font-size:30px;margin:0}p{font-size:17px;color:#58657a;margin:10px 0 26px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:22px}article{background:white;border:1px solid #e6ddd1;border-radius:16px;overflow:hidden}h2{font-size:17px;padding:14px;margin:0}article div{height:510px;overflow:hidden;border-top:1px solid #e6ddd1}img{width:100%;display:block}</style><h1>Kanji Connection · Modern Japanese Playful</h1><p>Protected local editorial preview · 30 chapters · 450 objective questions · Desktop, tablet and mobile verified</p><div class="grid">${html.join("")}</div>`,
  );
  await gallery
    .locator("img")
    .evaluateAll((imgs) => Promise.all(imgs.map((i) => i.decode())));
  await gallery.screenshot({
    path: resolve(folder, "contact-sheet.png"),
    fullPage: true,
  });
  console.log(JSON.stringify(report.summary));
} catch (error) {
  await writeFile(
    resolve(folder, "final-visual-review.json"),
    JSON.stringify({ ...final, failure: error.message }, null, 2),
  );
  console.error(error.message);
  process.exitCode = 1;
} finally {
  await browser.close();
}
