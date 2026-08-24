import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.describe("Accessibility", () => {
  test("page has no critical or serious axe violations", async ({ page }) => {
    await page.goto("/");
    const axeResults = await new AxeBuilder({ page }).analyze();
    // Filter to only critical and serious violations
    const criticalSerious = axeResults.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(criticalSerious).toEqual([]);
    // Optionally, log the violations for debugging
    if (axeResults.violations.length > 0) {
      console.log(`Axe violations found: ${JSON.stringify(axeResults.violations, null, 2)}`);
    }
  });
});
