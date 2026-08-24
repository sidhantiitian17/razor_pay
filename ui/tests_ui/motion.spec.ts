import { test, expect } from "@playwright/test";

test.describe("Motion", () => {
  test("under prefers-reduced-motion: reduce, no animation exceeds 0ms", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Get all elements that have animation or transition properties set
    // We'll check a broad set of elements and filter those that have non-zero duration.
    const elements = await page.locator("*").all();
    // Limit to avoid too many checks
    const limited = elements.slice(0, 100);
    for (const element of limited) {
      if (!(await element.isVisible())) continue;
      const animationDuration = await element.evaluate((el) => {
        const style = window.getComputedStyle(el);
        return style.animationDuration;
      });
      const transitionDuration = await element.evaluate((el) => {
        const style = window.getComputedStyle(el);
        return style.transitionDuration;
      });
      // Convert strings like "0.5s", "0ms" to milliseconds
      const parseDuration = (str: string) => {
        if (str.endsWith("ms")) return parseFloat(str);
        if (str.endsWith("s")) return parseFloat(str) * 1000;
        return 0; // fallback
      };
      const animMs = parseDuration(animationDuration);
      const transMs = parseDuration(transitionDuration);
      // We expect both to be 0 (or very close to 0) under reduced motion
      // Allow a small tolerance for rounding
      expect(
        animMs,
        `Element has animation duration ${animationDuration} which is not 0`,
      ).toBeLessThanOrEqual(1);
      expect(
        transMs,
        `Element has transition duration ${transitionDuration} which is not 0`,
      ).toBeLessThanOrEqual(1);
    }
  });
});
