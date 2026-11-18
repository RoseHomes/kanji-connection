// Read-only visual review. No content import, progress writes or Auth assertions.
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { chromium } from "../frontend/node_modules/@playwright/test/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const folder = path.join(root, "private/ui-review");
fs.mkdirSync(folder, { recursive: true });
const account = JSON.parse(
  fs.readFileSync(path.join(root, "private/live-auth-test/state.json"), "utf8"),
);
let context;
let stage = "session";
const statesOnly = process.argv.includes("--states-only");
const report = {
  application_write_requests: 0,
  screenshots: [],
  pages: [],
  lessons: [],
  browser_errors: [],
};
function save() {
  fs.writeFileSync(
    path.join(folder, statesOnly ? "states.json" : "review.json"),
    JSON.stringify(report, null, 2),
  );
}
function require(value, name) {
  if (!value) throw new Error(name);
}
try {
  context = await chromium.launchPersistentContext(
    path.join(folder, "browser-profile"),
    { channel: "msedge", headless: true },
  );
  await context.route("**/api/v1/**", (route) => {
    if (!["GET", "HEAD", "OPTIONS"].includes(route.request().method())) {
      report.application_write_requests++;
      return route.abort();
    }
    return route.continue();
  });
  const page = await context.newPage();
  page.on("pageerror", (error) =>
    report.browser_errors.push({ stage, name: error.name }),
  );
  await page.goto("http://127.0.0.1:5173/account");
  await page
    .locator('.account-page input[type="email"], .account-page .notice button')
    .first()
    .waitFor();
  if (await page.locator('input[type="email"]').isVisible()) {
    const password = execFileSync(
      "powershell.exe",
      [
        "-NoProfile",
        "-Command",
        "$v=[Console]::In.ReadToEnd(); $s=ConvertTo-SecureString -String $v; [System.Net.NetworkCredential]::new('', $s).Password",
      ],
      {
        input: fs.readFileSync(
          path.join(root, "private/live-auth-test/password.dpapi"),
          "utf8",
        ),
        encoding: "utf8",
        stdio: ["pipe", "pipe", "pipe"],
      },
    ).trim();
    await page.locator('input[type="email"]').fill(account.email);
    await page.locator('input[type="password"]').fill(password);
    await page.getByRole("button", { name: "เข้าสู่ระบบ", exact: true }).click();
    await page.waitForURL("**/dashboard");
  }
  if (statesOnly) {
    report.states = [];
    await page.setViewportSize({ width: 320, height: 900 });
    stage = "catalog_filter_and_private_notice";
    await page.goto("http://127.0.0.1:5173/lessons");
    await page
      .getByText("ส่วนตัวสำหรับพัฒนา · ยังไม่ผ่านการอนุมัติเผยแพร่", { exact: true })
      .waitFor();
    await page
      .getByRole("textbox", { name: "ค้นหาบทเรียน" })
      .fill("_no_match_ui_");
    await page.getByRole("button", { name: "ล้างตัวกรอง" }).click();
    await page.waitForFunction(
      () => document.querySelectorAll(".lesson-card").length === 30,
    );
    require(await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ), "HorizontalOverflow");
    await page.screenshot({ path: path.join(folder, "catalog-320-final.png") });
    report.states.push(stage);
    stage = "comparison_selection_and_back_navigation";
    await page.goto("http://127.0.0.1:5173/compare");
    const input = page.getByRole("textbox", { name: "ตัวอักษรที่ต้องการเปรียบเทียบ" });
    await input.fill("人,入");
    await page.getByRole("button", { name: "เปรียบเทียบ", exact: true }).click();
    await page.waitForFunction(
      () =>
        document.querySelector(".comparison .kanji-visual span")
          ?.textContent === "人",
    );
    await page.goBack();
    await page.waitForFunction(
      () => document.querySelector("#compare-characters")?.value === "林,森",
    );
    report.states.push(stage);
    stage = "read_only_lesson_and_table_of_contents";
    await page.goto("http://127.0.0.1:5173/lessons/chapter-02");
    await page.locator(".vocabulary-list").waitFor();
    require(await page
      .getByRole("button", { name: "บันทึกว่าอ่านจบแล้ว", exact: true })
      .isDisabled(), "WriteControlEnabled");
    await page.getByRole("link", { name: "คำศัพท์", exact: true }).click();
    require(await page.locator(".vocabulary-list").evaluate((e) => {
      const r = e.getBoundingClientRect();
      return r.top < innerHeight && r.bottom > 0;
    }), "TableOfContentsTarget");
    report.states.push(stage);
    stage = "service_error_and_retry";
    let failing = true;
    await page.route("**/api/v1/learning/lesson/chapter-02", (route) =>
      failing
        ? route.fulfill({
            status: 503,
            contentType: "application/json",
            body: "{}",
          })
        : route.continue(),
    );
    await page.goto("http://127.0.0.1:5173/lessons/chapter-02");
    await page.getByRole("alert").waitFor();
    failing = false;
    await page.getByRole("button", { name: "ลองใหม่", exact: true }).click();
    await page.locator(".vocabulary-list").waitFor();
    report.states.push(stage);
    stage = "empty_review_collection";
    await page.route("**/api/v1/me/review-cards", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "[]",
      }),
    );
    await page.goto("http://127.0.0.1:5173/review");
    await page
      .getByRole("heading", { name: "ยังไม่มีบัตรคันจิที่เปิดให้เข้าถึง", exact: true })
      .waitFor();
    report.states.push(stage);
    stage = "desktop_review_and_quiz_read_only";
    await page.unroute("**/api/v1/me/review-cards");
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("http://127.0.0.1:5173/review");
    await page.getByRole("button", { name: "เปิดคำตอบ", exact: true }).click();
    require(await page
      .getByRole("button", { name: "จำได้แล้ว ✓", exact: true })
      .isDisabled(), "WriteControlEnabled");
    await page
      .getByText("ส่วนตัวสำหรับพัฒนา · ยังไม่ผ่านการอนุมัติเผยแพร่", { exact: true })
      .waitFor();
    await page.goto("http://127.0.0.1:5173/quiz/chapter-02");
    await page.locator("textarea").fill("UI inspection only");
    require(await page
      .locator("form.learning-form button.primary")
      .isDisabled(), "WriteControlEnabled");
    report.states.push(stage);
  } else {
    for (const width of [320, 390, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      for (const route of [
        "/",
        "/lessons",
        "/explore",
        "/compare",
        "/lessons/chapter-02",
        "/quiz/chapter-02",
        "/review",
        "/dashboard",
        "/account",
        "/not-found",
      ]) {
        stage = `${width}:${route}`;
        await page.goto("http://127.0.0.1:5173" + route);
        await page.locator("main h1").waitFor();
        await page.waitForFunction(
          () =>
            !Array.from(document.querySelectorAll('[role="status"]')).some(
              (e) => e.textContent.includes("กำลังโหลด"),
            ),
        );
        await page.evaluate(() => document.fonts.ready);
        const metrics = await page.evaluate(() => ({
          width: document.documentElement.scrollWidth,
          height: document.documentElement.scrollHeight,
          alerts: Array.from(document.querySelectorAll('[role="alert"]')).map(
            (e) => e.textContent,
          ),
          sections: document.querySelectorAll(".lesson-section").length,
          vocabulary: document.querySelectorAll(".vocabulary-item").length,
          ruby: document.querySelectorAll("ruby rt").length,
        }));
        report.pages.push({ viewport_width: width, route, ...metrics });
        require(metrics.width <= width, "HorizontalOverflow");
        require(metrics.alerts.length === 0, "UnexpectedPageAlert");
        if (
          (width === 390 || width === 1440) &&
          [
            "/lessons",
            "/compare",
            "/lessons/chapter-02",
            "/dashboard",
          ].includes(route)
        ) {
          const name = `ui-${width}-${route.split("/").filter(Boolean).join("-")}.png`;
          await page.screenshot({
            path: path.join(folder, name),
            fullPage: true,
          });
          report.screenshots.push(name);
        }
      }
    }
    await page.setViewportSize({ width: 390, height: 900 });
    for (let chapter = 1; chapter <= 30; chapter++) {
      stage = `lesson:${chapter}`;
      await page.goto(
        `http://127.0.0.1:5173/lessons/chapter-${String(chapter).padStart(2, "0")}`,
      );
      await page.locator(".lesson-section").first().waitFor();
      const result = await page.evaluate(() => ({
        sections: document.querySelectorAll(".lesson-section").length,
        cards: document.querySelectorAll(".kanji-card").length,
        words: document.querySelectorAll(".vocabulary-item").length,
        overflow: document.documentElement.scrollWidth > innerWidth,
        sourcePages: document.querySelector(".lesson-section .subtle")
          ?.textContent,
        coreless: document.body.textContent.includes("แหล่งข้อมูลไม่ระบุแกนกลาง"),
        replacementCharacters: document
          .querySelector("main")
          .textContent.includes("\uFFFD"),
      }));
      report.lessons.push({ chapter, ...result });
      require(result.sections === 7 &&
        result.cards === 14 &&
        result.words === 8, "MissingLessonContent");
      require(!result.overflow &&
        !result.replacementCharacters, "LessonTextOrLayout");
      require(result.coreless ===
        [2, 4].includes(chapter), "IncorrectDiagramCore");
      if ([1, 4, 30].includes(chapter))
        await page.screenshot({
          path: path.join(folder, `lesson-${chapter}-390.png`),
          fullPage: true,
        });
    }
  }
  report.success =
    report.application_write_requests === 0 &&
    report.browser_errors.length === 0;
  save();
  console.log(
    JSON.stringify({
      success: report.success,
      responsive_pages: report.pages.length,
      focused_states: report.states?.length,
      imported_lessons_reviewed: report.lessons.length,
      application_write_requests: report.application_write_requests,
      browser_errors: report.browser_errors.length,
    }),
  );
} catch (error) {
  report.success = false;
  report.failed_stage = stage;
  report.error_name = error.name;
  report.issue = [
    "HorizontalOverflow",
    "UnexpectedPageAlert",
    "MissingLessonContent",
    "LessonTextOrLayout",
    "IncorrectDiagramCore",
  ].includes(error.message)
    ? error.message
    : "Review harness stopped; inspect locally";
  save();
  console.log(
    JSON.stringify({
      success: false,
      stage,
      issue: report.issue,
      pages_checked: report.pages.length,
    }),
  );
  process.exitCode = 1;
} finally {
  if (context) await context.close();
}
