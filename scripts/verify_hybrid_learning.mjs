// Real protected-preview QA. Capabilities and educational evidence stay private.
import { chromium } from "../frontend/node_modules/@playwright/test/index.mjs";
import AxeBuilder from "../frontend/node_modules/@axe-core/playwright/dist/index.mjs";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { createHash } from "node:crypto";
const root = resolve(import.meta.dirname, ".."),
  folder = resolve(root, "private/hybrid-learning"),
  shots = resolve(folder, "screenshots");
await mkdir(shots, { recursive: true });
const session = JSON.parse(
  await readFile(
    resolve(root, "private/editorial-preview/session.json"),
    "utf8",
  ),
);
const baseline = JSON.parse(
  await readFile(resolve(folder, "baseline.json"), "utf8"),
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
      chapters: [],
      screenshots: [],
      accessibility: [],
      navigation: [],
      pickers: [],
      quizzes: [],
      errors: [],
      writes: [],
      authRequests: [],
      fidelity: {},
      security: {},
      motion: {},
    };
delete report.failure;
const ensure = (ok, message) => {
  if (!ok) throw new Error(message);
};
const save = () =>
  writeFile(
    resolve(folder, "browser-verification.json"),
    JSON.stringify(report, null, 2),
  );
const normalized = (s) => s.replace(/\s+/g, " ").trim();
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object")
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((k) => [k, canonical(value[k])]),
    );
  return value;
}
const same = (a, b) =>
  JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
async function ready(page, selector) {
  await page.locator(selector).first().waitFor({ timeout: 35000 });
  await page.evaluate(() => document.fonts.ready);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > innerWidth + 1,
  );
  ensure(!overflow, "Horizontal page overflow " + new URL(page.url()).pathname);
  const text = await page.locator("body").innerText();
  ensure(
    !/PDF\s*(หน้า|page)|needs_review|catalog_visible|\.pdf\b|source_page_text|kanji-connection-extracted|revision_id/i.test(
      text,
    ),
    "Learner provenance leak",
  );
}
async function screenshot(page, name, { fullPage = true } = {}) {
  const file = resolve(shots, name + ".png");
  await page.screenshot({ path: file, fullPage, animations: "disabled" });
  report.screenshots.push(file);
}
async function axe(page, label) {
  const data = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  report.accessibility.push({
    label,
    violations: data.violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      nodes: v.nodes.map((n) => ({
        target: n.target,
        reason: n.failureSummary,
      })),
    })),
    incomplete: data.incomplete.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => ({
        target: n.target,
        reason: n.failureSummary,
      })),
    })),
    passes: data.passes.length,
  });
  await save();
}
async function picker(page, label, value) {
  const trigger = page.getByRole("combobox", { name: label, exact: true });
  await trigger.click();
  const list = page.getByRole("listbox");
  await list.waitFor();
  const popup = await page.locator(".picker-content").boundingBox();
  ensure(
    popup.x >= 0 &&
      popup.x + popup.width <= (await page.evaluate(() => innerWidth)) + 1,
    "Clipped picker " + label,
  );
  await page.getByRole("option", { name: value, exact: true }).click();
  await list.waitFor({ state: "hidden" });
}
async function jump(page, id) {
  const outline = page.locator(".chapter-outline");
  if (!(await outline.isVisible()))
    await page
      .getByRole("button", { name: "สารบัญและข้ามไปยังช่วงเรียน", exact: true })
      .click();
  await page.locator(`[data-stage-target="${id}"]`).click();
  await page.locator(`.guided-stage[data-stage="${id}"]`).waitFor();
}
async function officialRound(page, viewport) {
  await page.goto(
    session.origin + "/lessons/chapter-01?mode=guided&stage=review",
  );
  await ready(page, ".guided-stage");
  await page.getByRole("link", { name: "ไปแบบฝึกหัดได้ทันที", exact: true }).click();
  await ready(page, "input[type=radio]");
  ensure((await page.getByRole("textbox").count()) === 0, "Quiz needs typing");
  const questions = audit.chapters[0].objective_questions;
  for (let i = 0; i < questions.length; i++) {
    const q = questions[i],
      choice =
        i === 0
          ? q.options.find((o) => o.id !== q.correct_option_id).id
          : q.correct_option_id;
    await page.locator(`input[value="${choice}"]`).check();
    await page.getByRole("button", { name: /ตรวจคำตอบ/ }).click();
    await page.locator(".answer-feedback").waitFor();
    if (i === 0) {
      await screenshot(page, viewport + "-official-quiz-feedback");
      await axe(page, viewport + "-official-quiz-feedback");
    }
    await page
      .getByRole("button", {
        name: i === questions.length - 1 ? "ดูผลการฝึก" : "ข้อต่อไป",
        exact: true,
      })
      .click();
    if (i < questions.length - 1)
      await page
        .getByRole("heading", { name: questions[i + 1].prompt, exact: true })
        .waitFor();
  }
  await ready(page, ".results-panel");
  ensure(
    normalized(await page.locator(".result-score").innerText()).replace(
      /\s/g,
      "",
    ) === "14/15",
    "Incorrect official score",
  );
  await page.getByRole("button", { name: "ดูคำตอบทั้งรอบ", exact: true }).click();
  ensure(
    (await page.locator(".answer-review li").count()) === 15,
    "Review incomplete",
  );
  await screenshot(page, viewport + "-official-results");
  await axe(page, viewport + "-official-results");
  await page.getByRole("button", { name: "ลองข้อที่ยังสับสน", exact: true }).click();
  ensure(
    (await page.locator(".quiz-topline").innerText()).includes("ข้อ 1 จาก 1"),
    "Wrong-only retry changed",
  );
  await page
    .locator(`input[value="${questions[0].correct_option_id}"]`)
    .check();
  await page.getByRole("button", { name: /ตรวจคำตอบ/ }).click();
  await page.locator(".answer-feedback").waitFor();
  await page.getByRole("button", { name: "ดูผลการฝึก", exact: true }).click();
  await page.locator(".results-panel").waitFor();
  await page
    .getByRole("link", { name: "กลับไปทบทวนบทเรียน", exact: true })
    .click();
  await ready(page, ".guided-stage[data-stage=review]");
  report.quizzes.push({
    viewport,
    questions: 15,
    retry: 1,
    review: true,
    returnedToStage: "review",
  });
}
try {
  for (const [viewport, width, height] of [
    ["desktop", 1440, 1000],
    ["tablet", 820, 1180],
    ["mobile", 390, 844],
    ["small", 320, 800],
  ]) {
    if (report.quizzes.some((q) => q.viewport === viewport)) {
      console.log("Retaining completed " + viewport);
      continue;
    }
    console.log("Starting " + viewport + " " + width + "×" + height);
    const context = await browser.newContext({
      viewport: { width, height },
      reducedMotion: "reduce",
      ...(width <= 390 ? { isMobile: true, hasTouch: true } : {}),
    });
    ensure(
      (
        await context.request.get(session.origin + "/api/v1/learning/catalog")
      ).status() === 401,
      "Preview accessible without capability",
    );
    await context.request.get(session.open_url, { maxRedirects: 0 });
    const cookie = (await context.cookies()).find(
      (c) => c.name === "kanji_editorial_v2",
    );
    ensure(
      cookie?.httpOnly && cookie.sameSite === "Strict",
      "Preview cookie policy changed",
    );
    if (viewport === "desktop") {
      ensure(
        (
          await context.request.put(
            session.origin + "/api/v1/me/progress/chapter-01",
            { data: { progress: 100 } },
          )
        ).status() === 405,
        "Account writes enabled",
      );
      report.security = {
        unauthorized: 401,
        accountWriteDenied: 405,
        httpOnly: true,
        sameSite: "Strict",
      };
      const actualGroups = await (
        await context.request.get(
          session.origin + "/api/v1/learning/comparison-groups",
        )
      ).json();
      ensure(same(actualGroups, baseline.groups), "Comparison data changed");
      for (let n = 0; n < 30; n++) {
        const slug = `chapter-${String(n + 1).padStart(2, "0")}`;
        ensure(
          same(
            await (
              await context.request.get(
                session.origin + "/api/v1/learning/lesson/" + slug,
              )
            ).json(),
            baseline.lessons[n],
          ),
          "Lesson API changed " + slug,
        );
        ensure(
          same(
            await (
              await context.request.get(
                session.origin + "/api/v1/learning/practice/" + slug,
              )
            ).json(),
            baseline.questions[n],
          ),
          "Official questions changed " + slug,
        );
      }
      report.fidelity = {
        chapters: 30,
        groups: 94,
        questions: 450,
        lessonAndQuestionPayloadsUnchanged: true,
      };
    }
    const page = await context.newPage();
    page.setDefaultTimeout(20000);
    page.on("pageerror", (e) =>
      report.errors.push({ viewport, message: e.message }),
    );
    page.on("request", (r) => {
      const path = new URL(r.url()).pathname;
      if (path.includes("/auth/v1/")) report.authRequests.push(path);
      if (
        !["GET", "HEAD", "OPTIONS"].includes(r.method()) &&
        !/^\/api\/v1\/learning\/practice\/.+\/check$/.test(path)
      )
        report.writes.push({ path, method: r.method() });
    });
    for (let n = 1; n <= 30; n++) {
      if (
        report.chapters.some((c) => c.viewport === viewport && c.chapter === n)
      )
        continue;
      const slug = `chapter-${String(n).padStart(2, "0")}`,
        source = baseline.lessons[n - 1],
        expected = source.sections.flatMap((s) =>
          s.blocks.flatMap((b) => b.cards || []),
        );
      await page.goto(session.origin + "/lessons/" + slug);
      await ready(page, ".guided-stage");
      ensure(
        (await page.locator(".guided-stage").getAttribute("data-stage")) ===
          "discover",
        "New chapter not guided overview " + slug,
      );
      ensure(
        (await page.locator(".guided-stage .kanji-card").count()) === 0,
        "Entry renders whole document",
      );
      const targets = await page
        .locator("[data-stage-target]")
        .evaluateAll((nodes) => nodes.map((n) => n.dataset.stageTarget));
      ensure(
        targets.length >= 6 && targets.length <= 10,
        "Unreasonable stage count",
      );
      const seen = [];
      if (n === 1) {
        await screenshot(page, viewport + "-entry");
        await axe(page, viewport + "-entry");
        const start = await page
          .getByRole("button", { name: "เริ่มเรียน", exact: true })
          .boundingBox();
        ensure(
          start && start.y + start.height <= height,
          "Start action below first viewport",
        );
      }
      for (let i = 1; i < targets.length; i++) {
        await page
          .locator(".learning-actions")
          .getByRole("button")
          .last()
          .click();
        await ready(page, `.guided-stage[data-stage="${targets[i]}"]`);
        const items = page.locator(".guided-stage [data-card-character]");
        const characters = await items.evaluateAll((nodes) =>
          nodes.map((n) => n.dataset.cardCharacter),
        );
        if (characters.length) {
          ensure(
            characters.length >= 2 && characters.length <= 4,
            "Cards are not chunked",
          );
          seen.push(...characters);
          if (width <= 390) {
            ensure(
              (await page
                .locator(".guided-stage .kanji-card:visible")
                .count()) === 1,
              "Mobile defaults to a long card stack",
            );
            for (const glyph of characters) {
              await page
                .getByRole("button", { name: "ดู " + glyph, exact: true })
                .click();
              await page
                .locator(`[data-card-character="${glyph}"] .kanji-card`)
                .waitFor({ state: "visible" });
              const visible = page.locator(".guided-stage .kanji-card:visible");
              ensure((await visible.count()) === 1, "Card selection unclear");
              const card = expected.find((c) => c.character === glyph);
              ensure(
                normalized(await visible.innerText()).includes(
                  normalized(card.meaning_th),
                ),
                "Meaning missing",
              );
              ensure(
                normalized(await visible.innerText()).includes(
                  normalized(card.memory_note),
                ),
                "Mnemonic missing",
              );
            }
          } else {
            for (const glyph of characters) {
              const card = expected.find((c) => c.character === glyph);
              ensure(
                normalized(
                  await page
                    .locator(`[data-card-character="${glyph}"]`)
                    .innerText(),
                ).includes(normalized(card.memory_note)),
                "Mnemonic changed",
              );
            }
          }
          if (n === 1 && targets[i] === "learn-1") {
            await screenshot(page, viewport + "-learn");
            await axe(page, viewport + "-learn");
          }
        }
        if (n === 1 && targets[i] === "connect") {
          await screenshot(page, viewport + "-connect");
          await axe(page, viewport + "-connect");
        }
        if (n === 1 && targets[i] === "check") {
          await screenshot(page, viewport + "-checkpoint");
          await axe(page, viewport + "-checkpoint");
        }
      }
      ensure(
        same([...seen].sort(), expected.map((c) => c.character).sort()),
        "Guided coverage not 14 cards " + slug,
      );
      await page
        .getByRole("button", { name: "ดูบทเรียนทั้งหมด", exact: true })
        .click();
      await ready(page, ".full-lesson");
      ensure(
        (await page.locator("[data-card-summary]").count()) === 14,
        "Full summaries incomplete",
      );
      const details = page.locator(
        ".full-stage>.learning-disclosure>.disclosure-trigger",
      );
      for (let j = 0; j < (await details.count()); j++) {
        if ((await details.nth(j).getAttribute("aria-expanded")) === "false")
          await details.nth(j).click();
      }
      ensure(
        (await page.locator(".full-lesson .study-content").count()) === 14,
        "Full detailed cards missing",
      );
      ensure(
        (await page.locator(".full-lesson .sentence-card").count()) ===
          (n === 27 ? 2 : n === 29 ? 3 : 0),
        "Verified sentence missing",
      );
      if ([1, 15, 21, 27, 29, 30].includes(n)) {
        await screenshot(page, `${viewport}-${slug}-full`);
        await axe(page, `${viewport}-${slug}-full`);
      }
      report.chapters.push({
        viewport,
        chapter: n,
        stages: targets.length,
        guidedCards: seen.length,
        fullSummaries: 14,
        fullDetails: 14,
        optionalCheckSkipped: true,
      });
      await save();
      if (n % 5 === 0)
        console.log(`${viewport}: ${n}/30 guided and full chapters passed`);
    }
    // URL/history/refresh/card/rotation and return-context checks on the real app.
    await page.goto(
      session.origin + "/lessons/chapter-01?mode=guided&stage=learn-2",
    );
    await ready(page, ".guided-stage[data-stage=learn-2]");
    await page.reload();
    await ready(page, ".guided-stage[data-stage=learn-2]");
    await page.locator(".learning-actions").getByRole("button").last().click();
    await ready(page, ".guided-stage[data-stage=learn-3]");
    await page.goBack();
    await ready(page, ".guided-stage[data-stage=learn-2]");
    await page.goForward();
    await ready(page, ".guided-stage[data-stage=learn-3]");
    await page
      .getByRole("button", { name: "ดูบทเรียนทั้งหมด", exact: true })
      .click();
    await ready(page, ".full-lesson");
    await page.getByRole("button", { name: "เรียนเป็นช่วง", exact: true }).click();
    await ready(page, ".guided-stage[data-stage=learn-3]");
    if (width <= 390) {
      const glyph = await page
        .locator(".mobile-kanji-picker button[aria-label]")
        .nth(1)
        .getAttribute("aria-label");
      await page.getByRole("button", { name: glyph, exact: true }).click();
      ensure(
        new URL(page.url()).searchParams.get("card") === "1",
        "Focused card not linked",
      );
      await page.reload();
      await ready(page, ".guided-stage[data-stage=learn-3]");
      ensure(
        (await page
          .getByRole("button", { name: glyph, exact: true })
          .getAttribute("aria-pressed")) === "true",
        "Focused card lost on refresh",
      );
      await page.setViewportSize({ width: 844, height: width });
      await ready(page, ".guided-stage[data-stage=learn-3]");
      await page.setViewportSize({ width, height });
      ensure(
        (await page
          .getByRole("button", { name: glyph, exact: true })
          .getAttribute("aria-pressed")) === "true",
        "Rotation lost focus card",
      );
      await page
        .getByRole("button", { name: "ดูทั้งกลุ่มพร้อมกัน", exact: true })
        .click();
      ensure(
        (await page.locator(".guided-stage .kanji-card:visible").count()) > 1,
        "Show all cards fails",
      );
      await page
        .getByRole("button", { name: "กลับไปดูทีละตัว", exact: true })
        .click();
    }
    const explorerLink = page
      .locator(".guided-stage .kanji-card:visible .card-detail-link")
      .first();
    await explorerLink.click();
    await ready(page, ".kanji-detail-header");
    await page
      .getByRole("link", { name: "กลับไปยังช่วงที่กำลังเรียน", exact: true })
      .click();
    await ready(page, ".guided-stage[data-stage=learn-3]");
    await jump(page, "connect");
    await page.locator(".guided-comparison-links a").first().click();
    await ready(page, "table");
    await picker(
      page,
      "เลือกบทเปรียบเทียบ",
      `บท ${baseline.groups.at(-1).chapter} · ${baseline.groups.at(-1).title}`,
    );
    await page
      .getByRole("link", { name: "กลับไปยังช่วงที่กำลังเรียน", exact: true })
      .click();
    await ready(page, ".guided-stage[data-stage=connect]");
    await page.goto(
      session.origin + "/lessons/chapter-01?mode=guided&stage=learn-999",
    );
    await ready(page, ".guided-stage[data-stage=learn-4]");
    await page.goto(session.origin + "/lessons/chapter-01#lesson-section-5");
    await ready(page, ".full-lesson");
    ensure(
      new URL(page.url()).searchParams.get("stage") === "use",
      "Legacy section bookmark lost",
    );
    report.navigation.push({
      viewport,
      refresh: true,
      browserBackForward: true,
      modePosition: true,
      explorerReturn: true,
      comparisonReturn: true,
      removedSegmentFallback: true,
      legacyBookmark: true,
      rotation: width <= 390,
    });
    // Picker keyboard, touch and dismissal behavior.
    const chapterTrigger = page.getByRole("combobox", {
      name: "เลือกบทเรียน",
      exact: true,
    });
    await chapterTrigger.focus();
    await page.keyboard.press("Space");
    await page.getByRole("listbox").waitFor();
    ensure(
      (await page.getByRole("option").count()) === 30,
      "Chapter options missing",
    );
    await screenshot(page, viewport + "-chapter-picker");
    await axe(page, viewport + "-chapter-picker");
    await page.keyboard.press("End");
    await page.keyboard.press("Escape");
    ensure(
      await chapterTrigger.evaluate((n) => n === document.activeElement),
      "Picker Escape loses focus",
    );
    if (width <= 390) {
      await chapterTrigger.tap();
      await page
        .getByRole("option", {
          name: `บท 29 · ${baseline.lessons[28].title_th}`,
          exact: true,
        })
        .tap();
      await ready(page, ".hybrid-title");
      ensure(
        new URL(page.url()).pathname.endsWith("chapter-29"),
        "Touch chapter selection fails",
      );
    }
    await page.goto(session.origin + "/compare");
    await ready(page, "table");
    const trigger = page.getByRole("combobox", {
      name: "เลือกบทเปรียบเทียบ",
      exact: true,
    });
    await trigger.click();
    ensure(
      (await page.getByRole("option").count()) === 94,
      "Comparison choices missing",
    );
    await screenshot(page, viewport + "-comparison-picker");
    await axe(page, viewport + "-comparison-picker");
    await page.keyboard.press("Escape");
    const toExercise =
      viewport === "desktop"
        ? baseline.groups
        : [
            baseline.groups[0],
            baseline.groups[1],
            baseline.groups.find((g) => g.title === "休 / 体"),
            baseline.groups.at(-1),
          ];
    for (const group of toExercise) {
      await picker(
        page,
        "เลือกบทเปรียบเทียบ",
        `บท ${group.chapter} · ${group.title}`,
      );
      await page
        .getByRole("heading", { name: group.title, exact: true })
        .waitFor();
      ensure(
        (await page.getByRole("textbox").count()) === 0,
        "Comparison requires typing",
      );
      ensure(
        (await page.locator(".table-glyph").count()) ===
          (width <= 390 ? 2 : group.characters.length),
        "Comparison columns changed",
      );
    }
    await page.goto(session.origin + "/explore");
    await ready(page, ".explorer-tile");
    await page
      .getByRole("combobox", { name: "เลือกบทเรียนสำหรับสำรวจ", exact: true })
      .click();
    await page.getByRole("listbox").waitFor();
    ensure(
      (await page.getByRole("option").count()) === 31,
      "Explorer choices missing",
    );
    await screenshot(page, viewport + "-explorer-picker");
    await axe(page, viewport + "-explorer-picker");
    await page.keyboard.press("Home");
    await page.keyboard.press("End");
    await page.keyboard.press("Enter");
    await ready(page, ".explorer-tile");
    report.pickers.push({
      viewport,
      chapterOptions: 30,
      comparisonOptions: 94,
      comparisonSelections: toExercise.length,
      explorerOptions: 31,
      keyboard: true,
      touch: width <= 390,
      escapeFocus: true,
    });
    // Optional checkpoint answers survive switching modes; never gate navigation.
    await page.goto(
      session.origin + "/lessons/chapter-01?mode=guided&stage=check",
    );
    await ready(page, ".checkpoint input[type=radio]");
    const q = audit.chapters[0].objective_questions[0];
    await page.locator(`input[value="${q.correct_option_id}"]`).check();
    await page.getByRole("button", { name: /ตรวจคำตอบ/ }).click();
    await page.locator(".answer-feedback").waitFor();
    await page
      .getByRole("button", { name: "ดูบทเรียนทั้งหมด", exact: true })
      .click();
    await ready(page, ".full-lesson");
    await page.getByRole("button", { name: "เรียนเป็นช่วง", exact: true }).click();
    await ready(page, ".guided-stage[data-stage=check]");
    ensure(
      await page.locator(".checkpoint .answer-feedback").isVisible(),
      "Checkpoint answer reset by mode switch",
    );
    await page.locator(".learning-actions").getByRole("button").last().click();
    await ready(page, ".guided-stage[data-stage=review]");
    await officialRound(page, viewport);
    await context.close();
    await save();
  }
  const normal = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    reducedMotion: "no-preference",
  });
  await normal.request.get(session.open_url, { maxRedirects: 0 });
  const page = await normal.newPage();
  await page.goto(session.origin + "/lessons/chapter-01");
  await ready(page, ".guided-stage");
  await page.getByRole("button", { name: "เริ่มเรียน", exact: true }).click();
  await ready(page, ".guided-stage[data-stage=learn-1]");
  const expand = page.locator(".guided-stage .disclosure-trigger").first();
  await expand.click();
  await page.waitForTimeout(250);
  ensure(
    (await expand.getAttribute("aria-expanded")) === "true",
    "Animated disclosure fails",
  );
  await screenshot(page, "normal-motion-learn");
  report.motion = {
    normalTransition: true,
    expansion: true,
    reducedMotionContexts: 4,
  };
  await normal.close();
  for (const [file, sha] of Object.entries(baseline.protected_sha256)) {
    ensure(
      createHash("sha256")
        .update(await readFile(resolve(root, file)))
        .digest("hex") === sha,
      "Reviewed file changed " + file,
    );
  }
  ensure(report.errors.length === 0, "JavaScript errors");
  ensure(report.writes.length === 0, "Unexpected write");
  ensure(report.authRequests.length === 0, "Account auth request");
  report.summary = {
    chapterViewports: report.chapters.length,
    guidedCardOccurrences: report.chapters.reduce(
      (n, c) => n + c.guidedCards,
      0,
    ),
    fullCardOccurrences: report.chapters.reduce((n, c) => n + c.fullDetails, 0),
    officialQuizRounds: report.quizzes.length,
    officialAnswers: report.quizzes.reduce(
      (n, q) => n + q.questions + q.retry,
      0,
    ),
    axeScans: report.accessibility.length,
    axeViolations: report.accessibility.reduce(
      (n, a) => n + a.violations.length,
      0,
    ),
    screenshots: report.screenshots.length,
  };
  await save();
  console.log(JSON.stringify(report.summary));
} catch (error) {
  report.failure = error.message;
  await save();
  console.error(error.stack);
  process.exitCode = 1;
} finally {
  await browser.close();
}
