import { test, expect } from "@playwright/test";

test.describe("App Shell", () => {
  test("renders all 5 routes", async ({ page }) => {
    const routes = [
      { path: "/", label: "Runs" },
      { path: "/exceptions", label: "Exceptions" },
      { path: "/agent-trace", label: "Agent Trace" },
      { path: "/eval-lab", label: "Eval Lab" },
      { path: "/verify", label: "Verify" },
    ];

    for (const { path, label } of routes) {
      await page.goto(path);
      // Check that the route renders by verifying the sidebar link is active
      await expect(page.getByRole("link", { name: label, exact: true })).toBeVisible();
      await expect(page.getByRole("link", { name: label, exact: true })).toHaveAttribute(
        "aria-current",
        "page",
      );
    }
  });

  test("nav is keyboard reachable", async ({ page }) => {
    await page.goto("/");
    const links = page.getByRole("link");
    // Check that the 5 route links are focusable
    for (const { label } of [
      { path: "/", label: "Runs" },
      { path: "/exceptions", label: "Exceptions" },
      { path: "/agent-trace", label: "Agent Trace" },
      { path: "/eval-lab", label: "Eval Lab" },
      { path: "/verify", label: "Verify" },
    ]) {
      const link = page.getByRole("link", { name: label, exact: true });
      await link.focus();
      await expect(link).toBeFocused();
    }
  });
});
