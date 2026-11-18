import { expect, test } from "@playwright/test";

test("guest studies public sample content while personal review stays gated", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "森", exact: true }).click();
  await expect(page.getByText("もり", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "เลือกบทเรียน", exact: true }).click();
  await page.locator(".lesson-card.available a").click();
  await expect(
    page.getByRole("heading", { name: "ห้องทดลองคันจิ: ต้นไม้" }),
  ).toBeVisible();
  await expect(page.locator(".kanji-card")).toHaveCount(3);
  await page.getByRole("link", { name: "เปรียบเทียบตัวอักษร" }).click();
  await expect(page.locator(".comparison")).toHaveCount(2);
  await page.getByRole("button", { name: "森", exact: true }).click();
  await expect(page.locator(".comparison")).toHaveCount(3);
  await page.getByRole("link", { name: "ทบทวน", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "แฟลชการ์ดในจังหวะของคุณ" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "เรียนโดยไม่เข้าสู่ระบบ" }),
  ).toBeVisible();
});

test("mobile catalog filters and fits 360px viewport", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto("/lessons");
  await expect(page.locator(".lesson-card")).toHaveCount(1);
  await page.getByRole("textbox", { name: "ค้นหาบทเรียน" }).fill("ต้นไม้");
  await expect(page.locator(".lesson-card")).toHaveCount(1);
  await expect(
    page.getByRole("heading", { name: "ห้องทดลองคันจิ: ต้นไม้" }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(360);
  await page.goto("/");
  await expect(
    page.getByRole("link", { name: "เลือกบทเรียน", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(360);
  await page.screenshot({
    path: "../artifacts/home-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: "../artifacts/home-desktop.png",
    fullPage: true,
  });
});

test("API failure shows retry and an empty search explains no results", async ({
  page,
}) => {
  await page.route("**/api/v1/learning/kanjis*", (route) =>
    route.fulfill({ status: 503, body: "unavailable" }),
  );
  await page.goto("/explore");
  await expect(page.getByRole("alert")).toBeVisible();
  await page.unroute("**/api/v1/learning/kanjis*");
  await page.getByRole("button", { name: "ลองใหม่" }).click();
  await expect(page.locator(".kanji-card")).toHaveCount(3);
  await page.getByRole("textbox", { name: "ค้นหาคันจิ" }).fill("zzzz");
  await expect(
    page.getByText("ไม่พบคันจิที่ตรงกับคำค้น ลองเปลี่ยนหรือล้างคำค้น"),
  ).toBeVisible();
});
