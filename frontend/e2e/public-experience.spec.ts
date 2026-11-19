import { expect, test } from "@playwright/test";

test("production-style empty content never sends visitors to login or personal APIs", async ({
  page,
}) => {
  const personal: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.includes("/api/v1/me"))
      personal.push(request.url());
  });
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    return route.fulfill({
      contentType: "application/json",
      status: path.includes("/learning/lesson/") ? 404 : 200,
      body: JSON.stringify(
        path.endsWith("/health")
          ? { content_mode: "database", account_writes_enabled: false }
          : path.includes("/learning/lesson/")
            ? { error: { message: "Unavailable" } }
            : [],
      ),
    });
  });
  for (const [path, title] of [
    ["/", "บทเรียนสาธารณะกำลังเตรียมพร้อม"],
    ["/lessons", "บทเรียนสาธารณะกำลังเตรียมพร้อม"],
    ["/explore", "ยังไม่พบตัวอักษรในชุดนี้"],
    ["/quiz", "แบบฝึกหัดกำลังเตรียมพร้อม"],
    ["/compare", "ชุดเปรียบเทียบกำลังเตรียมพร้อม"],
  ]) {
    await page.goto(path);
    await expect(
      page.getByRole("heading", { name: title, exact: true }),
    ).toBeVisible();
    expect(new URL(page.url()).pathname).toBe(path);
  }
  await page.goto("/lessons/chapter-01");
  await expect(page.getByRole("alert")).toBeVisible();
  expect(new URL(page.url()).pathname).toBe("/lessons/chapter-01");
  for (const path of ["/dashboard", "/review"]) {
    await page.goto(path);
    await expect(
      page.getByRole("link", { name: "เรียนโดยไม่เข้าสู่ระบบ" }),
    ).toBeVisible();
  }
  expect(personal).toEqual([]);
});

test("mobile bottom navigation works with keyboard and reduced motion", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const quiz = page
    .getByRole("navigation", { name: "เมนูมือถือ" })
    .getByRole("link", { name: "แบบฝึกหัด", exact: true });
  await quiz.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/quiz$/);
  await expect(
    page
      .getByRole("navigation", { name: "เมนูมือถือ" })
      .getByRole("link", { name: "แบบฝึกหัด", exact: true }),
  ).toHaveAttribute("aria-current", "page");
});

for (const width of [360, 768, 1440]) {
  test(`study and account pages fit ${width}px and survive direct refresh`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    for (const path of [
      "/lessons/chapter-02",
      "/explore/木",
      "/compare",
      "/quiz/chapter-02",
      "/review",
      "/dashboard",
      "/account",
    ]) {
      await page.goto(path);
      await expect(page.locator("main h1")).toBeVisible();
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBeLessThanOrEqual(width);
      if (path === "/explore/木") {
        await expect(
          page.getByRole("heading", { name: "ต้นไม้; ไม้", exact: true }),
        ).toBeVisible();
        await page.reload();
        await expect(
          page.getByRole("heading", { name: "ต้นไม้; ไม้", exact: true }),
        ).toBeVisible();
      }
      if (
        width !== 768 &&
        ["/lessons/chapter-02", "/quiz/chapter-02", "/account"].includes(path)
      )
        await page.screenshot({
          path: `../private/ui-ux-redesign/screenshots/public-${width}-${path.split("/")[1]}.png`,
          fullPage: true,
        });
    }
  });
}
