// Dedicated-account book integration only. No signup, email or Auth regression tests.
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { chromium } from "../frontend/node_modules/@playwright/test/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const folder = path.join(root, "private/live-book-import");
const plan = JSON.parse(
  fs.readFileSync(path.join(folder, "learning-plan.json"), "utf8"),
);
const account = JSON.parse(
  fs.readFileSync(path.join(root, "private/live-auth-test/state.json"), "utf8"),
);
const report = {
  authentication_tests_repeated: false,
  temporary_content_created: 0,
};
let context;
let stage = "initialization";
function require(value) {
  if (!value) throw new Error("IntegrationAssertion");
}
function save() {
  fs.writeFileSync(
    path.join(folder, "learning-browser-results.json"),
    JSON.stringify(report, null, 2),
  );
}
function password() {
  return execFileSync(
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
}
async function launch() {
  const browser = await chromium.launchPersistentContext(
    path.join(folder, "browser-profile"),
    {
      channel: "msedge",
      headless: true,
    },
  );
  await browser.route("**/api/v1/**", async (route) => {
    const request = route.request();
    if (["GET", "HEAD", "OPTIONS"].includes(request.method()))
      return route.continue();
    const pathname = decodeURIComponent(new URL(request.url()).pathname);
    if (pathname.startsWith("/api/v1/me/attempts/")) {
      const q = plan.questions.find((q) => pathname.endsWith(q.key));
      if (q) {
        const body = request.postDataJSON();
        require(body.answer === q.answer);
        return route.continue({
          postData: JSON.stringify({ ...body, submission_id: q.submission_id }),
        });
      }
    }
    if (
      pathname === `/api/v1/me/progress/${plan.slug}` ||
      pathname === `/api/v1/me/reviews/${plan.character}`
    )
      return route.continue();
    return route.abort();
  });
  return browser;
}
async function api(
  page,
  endpoint,
  method = "GET",
  body = undefined,
  anonymous = false,
) {
  return page.evaluate(
    async ({ endpoint, method, body, anonymous, owner }) => {
      const { supabase } = await import("/src/supabase.ts");
      const { data } = await supabase.auth.getSession();
      if (!anonymous && data.session?.user.id !== owner)
        throw new Error("DedicatedAccountMismatch");
      const response = await fetch("/api/v1" + endpoint, {
        method,
        headers: {
          "Content-Type": "application/json",
          ...(!anonymous
            ? { Authorization: "Bearer " + data.session.access_token }
            : {}),
        },
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      });
      return { status: response.status, data: await response.json() };
    },
    { endpoint, method, body, anonymous, owner: plan.owner_id },
  );
}
async function action(page, match, run) {
  const response = page.waitForResponse(
    (r) =>
      decodeURIComponent(new URL(r.url()).pathname) === "/api/v1" + match &&
      r.request().method() !== "GET",
  );
  await run();
  const result = await response;
  require(result.status() === 200);
  return result.json();
}
try {
  require(account.user_id === plan.owner_id);
  stage = "normal_dedicated_account_session";
  context = await launch();
  let page = await context.newPage();
  await page.goto("http://127.0.0.1:5173/account");
  await page
    .locator('.account-page input[type="email"], .account-page .notice button')
    .first()
    .waitFor();
  if (await page.getByLabel("อีเมล", { exact: true }).isVisible()) {
    await page.getByLabel("อีเมล", { exact: true }).fill(account.email);
    await page.getByLabel("รหัสผ่าน", { exact: true }).fill(password());
    await page.getByRole("button", { name: "เข้าสู่ระบบ", exact: true }).click();
    await page.waitForURL("**/dashboard");
  }

  stage = "private_visibility";
  const catalog = await api(page, "/learning/lessons");
  require(
    catalog.status === 200 &&
      catalog.data.length === 30 &&
      catalog.data.every((l) => l.private_development),
  );
  for (const endpoint of ["/lessons", "/kanjis", "/learning/lessons"]) {
    const result = await api(page, endpoint, "GET", undefined, true);
    require(result.status === 200 && result.data.length === 0);
  }
  require(
    (await api(page, "/learning/lesson/" + plan.slug, "GET", undefined, true))
      .status === 404,
  );
  require(
    (await api(page, "/me/dashboard", "GET", undefined, true)).status === 401,
  );
  report.public_content_hidden = true;
  report.private_chapters_available = 30;

  stage = "persistent_lesson_progress";
  const first = await api(page, "/me/progress/" + plan.slug, "PUT", {
    progress: 50,
    expected_version: 0,
  });
  require(first.status === 200 && first.data.version === 1);
  await page.goto("http://127.0.0.1:5173/lessons/" + plan.slug);
  const completed = await action(page, "/me/progress/" + plan.slug, () =>
    page.getByRole("button", { name: "บันทึกว่าอ่านจบแล้ว", exact: true }).click(),
  );
  require(completed.progress === 100 && completed.version === 2);
  report.lesson_progress_ui = true;

  stage = "source_quizzes";
  await page.goto("http://127.0.0.1:5173/quiz/" + plan.slug);
  for (const q of plan.questions) {
    await page.locator("textarea").fill(q.answer);
    const graded = await action(page, "/me/attempts/" + q.key, () =>
      page.locator("form.learning-form button.primary").click(),
    );
    require(
      graded.persisted === true &&
        (q.manual
          ? graded.correct === null && graded.status === "needs_manual_review"
          : graded.correct === true && graded.status === "graded"),
    );
    if (q.manual)
      await page.getByRole("button", { name: "ข้อถัดไป →", exact: true }).click();
  }
  report.graded_quiz_ui = true;
  report.comparison_remains_manual = true;
  const q = plan.questions[1];
  require(
    (
      await api(page, "/me/attempts/" + q.key, "POST", {
        answer: q.answer,
        submission_id: q.submission_id,
      })
    ).status === 200,
  );
  report.idempotent_quiz_retry = true;

  stage = "flashcard_schedule";
  await page.goto("http://127.0.0.1:5173/review");
  const reveal = page.getByRole("button", { name: "เปิดคำตอบ", exact: true });
  await reveal.waitFor();
  require(
    (await reveal.locator('span[lang="ja"]').textContent()) === plan.character,
  );
  await reveal.click();
  const review = await action(page, "/me/reviews/" + plan.character, () =>
    page.getByRole("button", { name: "จำได้แล้ว ✓", exact: true }).click(),
  );
  require(
    review.interval === 1 && review.reviews === 1 && review.version === 1,
  );
  const second = await api(
    page,
    "/me/reviews/" + encodeURIComponent(plan.character),
    "PUT",
    { knew: true, expected_version: 1 },
  );
  require(
    second.status === 200 &&
      second.data.interval === 2 &&
      second.data.version === 2,
  );
  report.flashcard_ui = true;
  report.review_schedule_days = 2;

  stage = "stale_update_protection";
  require(
    (
      await api(page, "/me/progress/" + plan.slug, "PUT", {
        progress: 100,
        expected_version: 1,
      })
    ).status === 409,
  );
  require(
    (
      await api(
        page,
        "/me/reviews/" + encodeURIComponent(plan.character),
        "PUT",
        { knew: true, expected_version: 1 },
      )
    ).status === 409,
  );
  report.stale_updates_rejected = true;
  save();

  stage = "new_browser_session_persistence";
  await context.close();
  context = await launch();
  page = await context.newPage();
  await page.goto("http://127.0.0.1:5173/dashboard");
  await page
    .getByRole("heading", { name: "ความก้าวหน้ารายบท", exact: true })
    .waitFor({ timeout: 20000 });
  const dashboard = await api(page, "/me/dashboard");
  require(dashboard.status === 200);
  require(
    dashboard.data.lessons.some(
      (l) => l.slug === plan.slug && l.progress === 100 && l.version === 2,
    ),
  );
  require(dashboard.data.cards[plan.character].interval === 2);
  require(
    dashboard.data.quiz.graded === 1 &&
      dashboard.data.quiz.correct === 1 &&
      dashboard.data.quiz.pending === 1,
  );
  require((await page.locator("progress").getAttribute("value")) === "100");
  report.dashboard_ui = true;
  report.new_browser_session_progress_persisted = true;
  report.success = true;
  save();
  // End this ordinary work session; no Auth assertions or account deletion.
  await page.goto("http://127.0.0.1:5173/account");
  await page.getByRole("button", { name: "ออกจากระบบ", exact: true }).click();
  console.log(JSON.stringify(report));
} catch (error) {
  report.success = false;
  report.failed_stage = stage;
  report.error_type = error.name;
  save();
  console.log(JSON.stringify(report));
  process.exitCode = 1;
} finally {
  if (context) await context.close();
}
