import { test, expect } from "@playwright/test";
test("guest completes public quiz without storing personal history", async ({
  page,
}) => {
  await page.goto("/quiz/chapter-02");
  for (const [index, answer] of ["き", "はやし", "もり"].entries()) {
    await expect(page.getByRole("textbox")).toHaveCount(0);
    await page.getByRole("radio", { name: answer, exact: true }).check();
    await page.getByRole("button", { name: "ตรวจคำตอบ", exact: true }).click();
    await expect(page.getByText("ถูกต้อง เชื่อมโยงได้แล้ว!")).toBeVisible();
    await page
      .getByRole("button", {
        name: index === 2 ? "ดูผลการฝึก" : "ข้อต่อไป",
        exact: true,
      })
      .click();
  }
  await expect(page.getByText(/ตอบถูก 3 ข้อ/)).toBeVisible();
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
  await expect(page.getByText("ข้อ 1 จาก 3", { exact: true })).toBeVisible();
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
