import { test, expect } from "@playwright/test";
test("guest completes public quiz without storing personal history", async ({
  page,
}) => {
  await page.goto("/quiz/chapter-02");
  for (const answer of ["き", "はやし", "もり"]) {
    await page.getByRole("textbox", { name: "คำตอบของคุณ" }).fill(answer);
    await page.getByRole("button", { name: "ตรวจคำตอบ", exact: true }).click();
    await expect(page.getByText("ถูกต้อง ✓")).toBeVisible();
    await page.getByRole("button", { name: "ข้อถัดไป →" }).click();
  }
  await expect(page.getByText(/ตอบถูก 3 จาก 3/)).toBeVisible();
  expect(
    await page.evaluate(() =>
      localStorage.getItem("kanji-connection:learning:v1"),
    ),
  ).toBeNull();
  await page.goto("/dashboard");
  await expect(
    page.getByRole("link", { name: "เรียนโดยไม่เข้าสู่ระบบ" }),
  ).toBeVisible();
  await page.goto("/quiz/chapter-02");
  await page.reload();
  await expect(page.getByText("ข้อ 1 / 3", { exact: true })).toBeVisible();
});
test("account configuration state and learning layout fit a phone", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto("/account");
  await expect(page.getByLabel("อีเมล", { exact: true })).toBeVisible();
  await expect(
    page.getByText("ยังไม่ได้ตั้งค่าบัญชี คุณยังเรียนและทำแบบฝึกหัดสาธารณะได้"),
  ).toBeVisible();
  await page.goto("/dashboard");
  await expect(
    page.getByRole("heading", { name: "พื้นที่การเรียนรู้ของคุณ" }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(360);
});
