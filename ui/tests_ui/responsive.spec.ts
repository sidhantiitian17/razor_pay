import { test, expect } from "@playwright/test";

test.describe("Responsive", () => {
  const widths = [375, 768, 1440];
  for (const width of widths) {
    test(`no horizontal body scroll at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 });
      await page.goto("/");
      await page.waitForLoadState("networkidle");

      const horizontalScroll = await page.evaluate(() => {
        const body = document.body;
        return body.scrollWidth > body.clientWidth;
      });
      expect(horizontalScroll).toBe(false);
    });
  }
});
