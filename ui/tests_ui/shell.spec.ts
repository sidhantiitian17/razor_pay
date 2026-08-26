import { test, expect } from "@playwright/test";

// "/" is now the public marketing landing page (no sidebar); the operator
// shell with its 6 routes lives behind real Supabase Auth under these paths.
const ROUTES = [
  { path: "/runs", label: "Runs" },
  { path: "/dashboard", label: "Run Dashboard" },
  { path: "/exceptions", label: "Exceptions" },
  { path: "/agent-trace", label: "Agent Trace" },
  { path: "/eval-lab", label: "Eval Lab" },
  { path: "/verify", label: "Verify" },
];

test.describe("App Shell", () => {
  test("renders all 6 authenticated routes", async ({ page }) => {
    for (const { path, label } of ROUTES) {
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
    await page.goto("/runs");
    for (const { label } of ROUTES) {
      const link = page.getByRole("link", { name: label, exact: true });
      await link.focus();
      await expect(link).toBeFocused();
    }
  });
});
