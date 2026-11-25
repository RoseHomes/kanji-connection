import { expect, test, type Locator, type Page } from "@playwright/test";
import type { ItemPage, LearningUnit, PathDetail } from "../src/learning-paths";

const unitSummary = {
  unit_key: "intro",
  title_th: "อ่านคำศัพท์ในบริบทและทบทวนคำอ่านภาษาญี่ปุ่น",
  intro_th: "ลองอ่านตัวอย่างแล้วกลับมาทบทวนคำศัพท์ตามลำดับที่สะดวก",
  available_count: 1,
};
const items: ItemPage = {
  items: [
    {
      id: 1,
      type: "sentence",
      text: "日本語の本を読みながら新しい言葉をノートに書きました。",
      reading:
        "にほんごのほんをよみながらあたらしいことばをノートにかきました。",
      meaning_th: "ฉันจดคำศัพท์ใหม่ลงในสมุดระหว่างอ่านหนังสือภาษาญี่ปุ่น",
      usage_notes: "",
      context_note_th: "",
      level: 3,
      required: true,
      unit_key: "intro",
      path_slug: "n3",
    },
  ],
  next_cursor: null,
  total: 1,
};

async function mockPaths(page: Page) {
  await page.route("**/api/v1/learning/paths**", (route) => {
    const url = new URL(route.request().url());
    const [kind, slug, view] = url.pathname.split("/").slice(5);
    const jlpt = (kind || url.searchParams.get("kind")) === "jlpt";
    const path: PathDetail = {
      kind: jlpt ? "jlpt" : "category",
      slug: jlpt ? "n3" : "reading",
      level: jlpt ? 3 : null,
      title_th: jlpt ? "JLPT N3" : "อ่านคำศัพท์ภาษาญี่ปุ่นจากตัวอย่างในชีวิตประจำวัน",
      summary_th: unitSummary.intro_th,
      counts: { kanji: 0, vocabulary: 0, sentence: 1 },
      units: [unitSummary],
      reference: jlpt
        ? {
            source_key: "example",
            source_url: "https://example.com",
            attribution: "ชื่อแหล่งอ้างอิงสำหรับทดสอบการตัดบรรทัด",
            license: "CC BY-SA 4.0",
            version: "sample-123",
            totals: { kanji: 1, vocabulary: 1, sentence: 1 },
          }
        : null,
    };
    const unit: LearningUnit = {
      ...unitSummary,
      path,
      items: items.items,
      previous_unit_key: "previous",
      next_unit_key: "next",
      practice_available: false,
    };
    if (slug === "n4") return route.fulfill({ status: 404, json: {} });
    if (view === "items")
      return route.fulfill({
        json: url.searchParams.get("q")
          ? { items: [], total: 0, next_cursor: null }
          : items,
      });
    return route.fulfill({
      json: view === "units" ? unit : slug ? path : [path],
    });
  });
}

async function expectPageFits(page: Page) {
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(page.viewportSize()!.width);
}

async function expectSeparated(first: Locator, second: Locator) {
  const a = (await first.boundingBox())!;
  const b = (await second.boundingBox())!;
  const horizontal = Math.max(b.x - a.x - a.width, a.x - b.x - b.width);
  const vertical = Math.max(b.y - a.y - a.height, a.y - b.y - b.height);
  expect(Math.max(horizontal, vertical)).toBeGreaterThanOrEqual(7);
}

for (const width of [320, 375, 390, 430, 768, 1440]) {
  test(`public routes and unfinished JLPT state fit ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await mockPaths(page);

    for (const [url, selector] of [
      ["/", ".home-cta"],
      ["/lessons", ".lesson-card"],
      ["/lessons/chapter-02?mode=guided", ".guided-stage"],
      ["/lessons/chapter-02?mode=full", ".full-stage"],
      ["/categories", ".lesson-card"],
      ["/categories/reading", ".path-item-list .vocabulary-item"],
      ["/categories/reading/units/intro?mode=guided", ".guided-stage"],
      ["/jlpt", ".lesson-card"],
      ["/jlpt/n3", ".path-item-list .vocabulary-item"],
      ["/jlpt/n3/units/intro?mode=full", ".full-stage"],
      ["/explore", ".explorer-tile"],
      ["/explore/木", ".kanji-detail-header"],
      ["/compare", ".comparison-table"],
      ["/quiz", ".practice-chapter"],
      ["/quiz/chapter-02", ".question-panel"],
      ["/review", ".access-card"],
      ["/dashboard", ".access-card"],
      ["/account", ".learning-form"],
      ["/missing", "main h1"],
    ]) {
      await page.goto(url);
      await expect(page.locator(selector).first()).toBeVisible();
      await expectPageFits(page);
    }

    await page.goto("/jlpt/n4");
    const back = page.locator(".path-back");
    const heading = page.getByRole("heading", { level: 1 });
    const status = page.getByRole("heading", { name: "กำลังเตรียมหน่วยเรียน" });
    await expect(status).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expectSeparated(back, heading);
    await expectSeparated(heading, status);
    await expectSeparated(page.locator(".empty-state .icon-tile"), status);
    expect((await status.boundingBox())!.height).toBeLessThanOrEqual(48);
    await expectPageFits(page);

    if (width === 320) {
      await page.goto("/jlpt/n3");
      await page.getByRole("searchbox", { name: "ค้นหาในเส้นทาง" }).fill("なし");
      await expect(
        page.getByRole("heading", { name: "ไม่พบรายการตามตัวกรอง" }),
      ).toBeVisible();
      await expectPageFits(page);
    }
  });
}

test("loading and error notices keep retry, link and supporting text spaced on mobile", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 900 });
  let fail = true;
  let releaseResponse!: () => void;
  const pending = new Promise<void>((resolve) => {
    releaseResponse = resolve;
  });
  await page.route("**/api/v1/learning/paths?**", async (route) => {
    await pending;
    if (fail)
      return route.fulfill({
        status: 503,
        json: {
          error: { message: "กำลังเชื่อมต่อใหม่ กรุณากลับมาอีกครั้งเมื่อการเชื่อมต่อพร้อม" },
        },
      });
    return route.fulfill({ json: [] });
  });

  await page.goto("/categories");
  await expect(
    page.getByRole("status").filter({ hasText: "กำลังโหลดข้อมูล" }),
  ).toBeVisible();
  releaseResponse();
  const error = page.getByRole("alert");
  const retry = error.getByRole("button", { name: "ลองใหม่" });
  const lessons = error.getByRole("link", { name: "ดูบทเรียนที่เข้าถึงได้" });
  await expect(retry).toBeVisible();
  await expectSeparated(error.locator("p"), error.locator(".action-group"));
  await expectSeparated(retry, lessons);
  await expectSeparated(error.locator(".action-group"), error.locator("small"));
  for (const action of [retry, lessons])
    expect((await action.boundingBox())!.height).toBeGreaterThanOrEqual(44);
  await expectPageFits(page);

  fail = false;
  await retry.click();
  await expect(
    page.getByRole("heading", { name: "ยังไม่มีหมวดที่เปิดให้เรียน" }),
  ).toBeVisible();
});

test("quiz results wrap actions and the answer dialog fits a narrow screen", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto("/quiz/chapter-02");
  for (const [index, answer] of ["き", "はやし", "もり"].entries()) {
    await page.getByRole("radio", { name: answer, exact: true }).check();
    await page.getByRole("button", { name: "ตรวจคำตอบ", exact: true }).click();
    await page
      .getByRole("button", {
        name: index === 2 ? "ดูผลการฝึก" : "ข้อต่อไป",
        exact: true,
      })
      .click();
  }
  const showAnswers = page.getByRole("button", { name: "ดูคำตอบทั้งรอบ" });
  await expect(showAnswers).toBeVisible();
  await expectSeparated(
    showAnswers,
    page.getByRole("button", { name: "เริ่มรอบใหม่" }),
  );
  await showAnswers.click();
  const details = page.getByRole("button", { name: "ดูรายละเอียด ข้อ 1" });
  await details.click();
  const dialog = page.getByRole("dialog", { name: "ข้อ 1" });
  const close = dialog.getByRole("button", { name: "ปิดรายละเอียด" });
  await expect(dialog).toBeVisible();
  await expectSeparated(dialog.getByRole("heading"), close);
  expect((await close.boundingBox())!.height).toBeGreaterThanOrEqual(44);
  await expectPageFits(page);
  await close.click();
  await expect(details).toBeFocused();
});
