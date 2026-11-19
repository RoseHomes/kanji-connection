// Protected, real-browser verification. Never log or embed the preview capability.
import { chromium } from "../frontend/node_modules/@playwright/test/index.mjs";
import AxeBuilder from "../frontend/node_modules/@axe-core/playwright/dist/index.mjs";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const folder = resolve(root, "private/ui-ux-redesign");
const shots = resolve(folder, "screenshots");
await mkdir(shots, { recursive: true });
const session = JSON.parse(
  await readFile(
    resolve(root, "private/editorial-preview/session.json"),
    "utf8",
  ),
);
const audit = JSON.parse(
  await readFile(
    resolve(root, "private/learning-presentation/mcq-presentation-v1.json"),
    "utf8",
  ),
);
const browser = await chromium.launch({ channel: "msedge", headless: true });
const report = process.argv.includes("--resume")
  ? JSON.parse(
      await readFile(resolve(folder, "browser-verification.json"), "utf8"),
    )
  : {
      viewports: [],
      chapters: [],
      accessibility: [],
      screenshots: [],
      errors: [],
      forbiddenWrites: [],
      security: {},
      keyboard: {},
      reducedMotion: {},
      zoom: {},
    };
delete report.failure;
const ensure = (condition, message) => {
  if (!condition) throw new Error(message);
};
const origin = session.origin;
const save = async () =>
  writeFile(
    resolve(folder, "browser-verification.json"),
    JSON.stringify(report, null, 2),
  );
const forbiddenUI =
  /PDF\s*(หน้า|page)|\.pdf\b|kanji-connection-extracted|revision_id|comparison-c|needs_review|catalog_visible|source_page_text/i;
async function ready(page, selector) {
  await page.locator(selector).first().waitFor({ timeout: 45000 });
  await page.evaluate(() => document.fonts.ready);
  ensure(
    !(await page
      .locator("body")
      .innerText()
      .then((t) => forbiddenUI.test(t))),
    "Internal provenance visible on " + new URL(page.url()).pathname,
  );
  ensure(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
    "Horizontal overflow on " + new URL(page.url()).pathname,
  );
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
  ensure(
    overflow.length === 0,
    "Clipped layout overflow: " + overflow.join(","),
  );
}
async function screenshot(page, name, fullPage = true) {
  const path = resolve(shots, name + ".png");
  await page.screenshot({ path, fullPage });
  report.screenshots.push(path);
}
async function axe(page, label) {
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  report.accessibility.push({
    label,
    violations: result.violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      description: v.description,
      nodes: v.nodes.map((n) => ({
        target: n.target,
        summary: n.failureSummary,
      })),
    })),
    incomplete: result.incomplete.map((v) => ({
      id: v.id,
      nodes: v.nodes.length,
    })),
    passes: result.passes.length,
  });
  await save();
}
async function round(page, chapter, viewport, wrongFirst = false) {
  const slug = `chapter-${String(chapter.chapter).padStart(2, "0")}`;
  if (new URL(page.url()).pathname !== `/quiz/${slug}`)
    await page.goto(`${origin}/quiz/${slug}`);
  await ready(page, "input[type=radio]");
  ensure(
    (await page.locator("textarea,input[type=text]").count()) === 0,
    "Quiz requires typing",
  );
  const live = await (
    await page.request.get(`${origin}/api/v1/learning/practice/${slug}`)
  ).json();
  const keys = new Map(chapter.objective_questions.map((q) => [q.id, q]));
  ensure(live.length === 15, "Incomplete chapter quiz");
  for (let i = 0; i < live.length; i++) {
    const q = live[i],
      key = keys.get(q.id);
    ensure(key, "Unknown question identity");
    const correct = key.correct_option_id;
    const choice =
      wrongFirst && i === 0
        ? q.options.find((o) => o.id !== correct).id
        : correct;
    await page.locator(`input[type=radio][value="${choice}"]`).check();
    await page.getByRole("button", { name: /ตรวจคำตอบ/ }).click();
    await page.locator(".answer-feedback").waitFor();
    const normalize = (t) => t.replace(/\s+/g, " ").trim();
    ensure(
      await page
        .locator(".answer-feedback")
        .innerText()
        .then((t) => normalize(t).includes(normalize(key.explanation))),
      "Incorrect explanation " + slug + " question " + (i + 1),
    );
    if (i === 0 && chapter.chapter === 1) {
      await screenshot(page, `${viewport}-quiz-feedback`);
      await axe(page, `${viewport}-quiz-feedback`);
    }
    await page
      .getByRole("button", {
        name: i === live.length - 1 ? "ดูผลการฝึก" : "ข้อต่อไป",
        exact: true,
      })
      .click();
    if (i < live.length - 1)
      await page
        .getByRole("heading", { name: live[i + 1].prompt, exact: true })
        .waitFor();
  }
  await ready(page, ".results-panel");
  ensure(
    await page
      .locator(".result-score")
      .innerText()
      .then((t) => t.replace(/\s/g, "") === (wrongFirst ? "14/15" : "15/15")),
    "Incorrect result total",
  );
  await page.getByRole("button", { name: "ดูคำตอบทั้งรอบ", exact: true }).click();
  ensure(
    (await page.locator(".answer-review li").count()) === 15,
    "Incomplete answer review",
  );
  if (chapter.chapter === 1) {
    await screenshot(page, `${viewport}-quiz-results`);
    await axe(page, `${viewport}-quiz-results`);
  }
  if (wrongFirst) {
    await page
      .getByRole("button", { name: "ลองข้อที่ยังสับสน", exact: true })
      .click();
    await page.locator("input[type=radio]").first().waitFor();
    ensure(
      await page
        .locator(".quiz-topline")
        .innerText()
        .then((t) => t.includes("ข้อ 1 จาก 1")),
      "Wrong-only retry did not narrow queue",
    );
    await page
      .locator(`input[value="${keys.get(live[0].id).correct_option_id}"]`)
      .check();
    await page.getByRole("button", { name: /ตรวจคำตอบ/ }).click();
    await page.locator(".answer-feedback").waitFor();
    await page.getByRole("button", { name: "ดูผลการฝึก", exact: true }).click();
    await ready(page, ".results-panel");
    ensure(
      await page
        .locator(".result-score")
        .innerText()
        .then((t) => t.replace(/\s/g, "") === "1/1"),
      "Retry result incorrect",
    );
  }
}

try {
  for (const [name, width, height] of [
    ["desktop", 1440, 1000],
    ["tablet", 820, 1180],
    ["mobile", 390, 844],
  ]) {
    if (report.viewports.some((v) => v.name === name && v.chapters === 30)) {
      console.log(`Retaining completed ${name} verification`);
      continue;
    }
    console.log(`Starting ${name} ${width}×${height}`);
    const context = await browser.newContext({
      viewport: { width, height },
      reducedMotion: "reduce",
    });
    if (name === "desktop") {
      ensure(
        (
          await context.request.get(origin + "/api/v1/learning/catalog")
        ).status() === 401,
        "Preview API open without capability",
      );
      report.security.unauthorizedPreview = 401;
    }
    ensure(
      (
        await context.request.get(session.open_url, { maxRedirects: 0 })
      ).status() === 303,
      "Preview authorization failed",
    );
    const cookie = (await context.cookies()).find(
      (c) => c.name === "kanji_editorial_v2",
    );
    ensure(
      cookie?.httpOnly && cookie.sameSite === "Strict",
      "Insecure preview cookie",
    );
    if (name === "desktop") {
      report.security.httpOnlyStrictCookie = true;
      const write = await context.request.put(
        origin + "/api/v1/me/progress/chapter-01",
        { data: { progress: 100 } },
      );
      ensure(write.status() === 405, "Account writes enabled");
      report.security.accountWriteDenied = 405;
      const fileProbe = await context.request.get(
        origin +
          "/@fs/" +
          resolve(root, "private/editorial-preview/session.json").replaceAll(
            "\\",
            "/",
          ),
      );
      ensure(
        [403, 404].includes(fileProbe.status()),
        "Vite serves private capability",
      );
      report.security.privateFileDenied = fileProbe.status();
    }
    const page = await context.newPage();
    page.setDefaultTimeout(20000);
    page.on("pageerror", (e) =>
      report.errors.push({ viewport: name, error: e.message }),
    );
    page.on("request", (r) => {
      const path = new URL(r.url()).pathname;
      if (
        !["GET", "HEAD", "OPTIONS"].includes(r.method()) &&
        !/^\/api\/v1\/learning\/practice\/.+\/check$/.test(path)
      )
        report.forbiddenWrites.push({ method: r.method(), path });
    });
    page.on("response", (r) => {
      if (r.url().includes("/api/") && r.status() >= 400)
        report.errors.push({
          viewport: name,
          path: new URL(r.url()).pathname,
          status: r.status(),
        });
    });
    for (const [label, path, selector] of [
      ["home", "/", ".hero-kanji-pickers"],
      ["catalog", "/lessons", ".lesson-card"],
      ["explorer", "/explore", ".explorer-tile"],
      ["detail", "/explore/人", ".kanji-detail-header"],
      ["account", "/account", "h1"],
      ["dashboard", "/dashboard", "h1"],
      ["review", "/review", "h1"],
    ]) {
      await page.goto(origin + path);
      await ready(page, selector);
      await screenshot(page, `${name}-${label}`);
      await axe(page, `${name}-${label}`);
    }
    // Every curated group is selectable without typing; 3-way sets use pair focus on mobile.
    await page.goto(origin + "/compare");
    await ready(page, "table");
    const groups = await (
      await context.request.get(origin + "/api/v1/learning/comparison-groups")
    ).json();
    for (const group of groups) {
      await page.locator(".select-label select").selectOption(group.id);
      await page
        .getByRole("heading", { name: group.title, exact: true })
        .waitFor();
      ensure(
        (await page.locator("input,textarea").count()) === 0,
        "Comparison text entry found",
      );
      ensure(
        (await page.locator(".table-glyph").count()) ===
          (width <= 700 ? 2 : group.characters.length),
        "Incorrect comparison columns",
      );
    }
    for (const [label, glyphs] of [
      ["triad", ["大", "犬", "太"]],
      ["people", ["人", "入"]],
      ["rest-body", ["休", "体"]],
    ]) {
      const group = groups.find(
        (g) =>
          g.characters.map((c) => c.character).join(",") === glyphs.join(","),
      );
      ensure(group, "Required comparison group missing");
      await page.locator(".select-label select").selectOption(group.id);
      await ready(page, "table");
      await screenshot(page, `${name}-compare-${label}`);
      await axe(page, `${name}-compare-${label}`);
      if (width <= 700 && glyphs.length === 3) {
        await page
          .getByRole("button", { name: "大 / 太", exact: true })
          .click();
        ensure(
          await page
            .locator(".table-glyph")
            .allTextContents()
            .then((t) => t.join(",") === "大,太"),
          "Mobile pair focus failed",
        );
      }
    }
    if (name === "desktop") {
      await page.goto(origin + "/compare");
      await ready(page, "table");
      await page.locator(".group-buttons button").first().focus();
      await page.keyboard.press("Tab");
      ensure(
        await page.evaluate(() =>
          document.activeElement.matches(".group-buttons button"),
        ),
        "Keyboard cannot traverse groups",
      );
      await page.keyboard.press("Enter");
      await page.goto(origin + "/quiz/chapter-01");
      await ready(page, "input[type=radio]");
      await page.locator("input[type=radio]").first().focus();
      await page.keyboard.press("ArrowDown");
      ensure(
        await page.locator("input[type=radio]").nth(1).isChecked(),
        "Native radio arrow navigation failed",
      );
      await page.keyboard.press("Tab");
      ensure(
        await page
          .getByRole("button", { name: /ตรวจคำตอบ/ })
          .evaluate((el) => el === document.activeElement),
        "Check button inaccessible by keyboard",
      );
      report.keyboard = {
        comparisonButtons: true,
        radioArrowSelection: true,
        explicitCheck: true,
      };
      report.reducedMotion = {
        preference: await page.evaluate(
          () => matchMedia("(prefers-reduced-motion: reduce)").matches,
        ),
        activeAnimations: await page.evaluate(
          () =>
            document
              .getAnimations()
              .filter(
                (a) =>
                  a.playState === "running" &&
                  a.effect?.getComputedTiming().duration > 1,
              ).length,
        ),
      };
    }
    for (const chapter of audit.chapters) {
      if (
        report.chapters.some(
          (c) => c.viewport === name && c.chapter === chapter.chapter,
        )
      )
        continue;
      const slug = `chapter-${String(chapter.chapter).padStart(2, "0")}`;
      await page.goto(origin + "/lessons/" + slug);
      await ready(page, ".study-content");
      ensure(
        (await page.locator(".study-content").count()) === 14,
        "Missing cards " + slug,
      );
      ensure(
        (await page.locator(".sentence-card").count()) ===
          (chapter.chapter === 27 ? 2 : chapter.chapter === 29 ? 3 : 0),
        "Missing phrases",
      );
      if ([8, 21].includes(chapter.chapter))
        ensure(
          (await page.locator(".supplementary-study").count()) === 1,
          "Supplementary panel missing",
        );
      await screenshot(page, `${name}-${slug}`);
      if ([1, 2, 8, 10, 21, 27, 29, 30].includes(chapter.chapter))
        await axe(page, `${name}-${slug}`);
      // Follow a real lesson CTA before completing its entire 15-item round.
      await page.locator(".practice-invitation a").click();
      await ready(page, "input[type=radio]");
      await round(page, chapter, name, chapter.chapter === 1);
      report.chapters.push({
        viewport: name,
        chapter: chapter.chapter,
        cards: 14,
        questions: 15,
        results: true,
        review: true,
        wrongOnlyRetry: chapter.chapter === 1,
      });
      await save();
      if (chapter.chapter % 5 === 0)
        console.log(
          `${name}: ${chapter.chapter}/30 full lesson and quiz flows passed`,
        );
    }
    report.viewports.push({
      name,
      width,
      height,
      chapters: 30,
      curatedGroups: groups.length,
    });
    await context.close();
  }
  // A 200% browser-equivalent CSS viewport on a 1440px desktop is 720px.
  const zoomContext = await browser.newContext({
    viewport: { width: 720, height: 500 },
    deviceScaleFactor: 2,
    reducedMotion: "reduce",
  });
  await zoomContext.request.get(session.open_url, { maxRedirects: 0 });
  const zoomPage = await zoomContext.newPage();
  for (const [path, selector, label] of [
    ["/lessons/chapter-01", ".study-content", "lesson"],
    ["/compare", "table", "compare"],
    ["/quiz/chapter-01", "input[type=radio]", "quiz"],
  ]) {
    await zoomPage.goto(origin + path);
    await ready(zoomPage, selector);
    await screenshot(zoomPage, "zoom-200-" + label);
    await axe(zoomPage, "zoom-200-" + label);
  }
  report.zoom = {
    equivalentScale: 2,
    cssViewport: 720,
    deviceScaleFactor: 2,
    overflow: false,
  };
  await zoomContext.close();
  ensure(report.errors.length === 0, "Browser errors observed");
  ensure(report.forbiddenWrites.length === 0, "Unexpected write request");
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
    screenshots: report.screenshots.length,
  };
  await save();
  console.log(JSON.stringify(report.summary));
} catch (error) {
  report.failure = error.message;
  await save();
  console.error(error.message);
  process.exitCode = 1;
} finally {
  await browser.close();
}
