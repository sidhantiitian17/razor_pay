import { test, expect } from "@playwright/test";

test.describe("Page States", () => {
  test("shows skeleton when state=loading", async ({ page }) => {
    await page.goto("/runs?state=loading");
    // Check for skeleton element: we can look for an element with aria-busy="true" (from PanelSkeleton)
    await expect(page.getByRole("status", { name: /loading data/i })).toBeVisible();
    // Alternatively, we can look for the Skeleton component from @/components/ui/skeleton
    // But we don't know the exact class. We'll rely on the aria-label from PanelSkeleton.
    // In PanelSkeleton, we see: <span className="sr-only">Loading data</span>
    // So we can look for a text "Loading data" that is hidden but present.
    await expect(page.getByText("Loading data", { exact: false })).toBeAttached();
  });

  test("shows empty state when state=empty", async ({ page }) => {
    await page.goto("/runs?state=empty");
    // Check for EmptyState: we can look for the Database icon and the title/hint.
    // From page-states.tsx, EmptyState renders:
    // <Database className="size-5 text-muted-foreground" aria-hidden="true" />
    // <div className="text-sm font-medium text-foreground">{title}</div>
    // <p className="max-w-md text-sm text-muted-foreground">{hint}</p>
    // We can check for the title and hint text from the Runs route.
    // For Runs route, emptyTitle="No runs loaded", emptyHint="Runs appear once the reconciliation database is enabled and the frozen schema is applied. No figures are rendered before then."
    await expect(page.getByText("No runs loaded", { exact: true })).toBeVisible();
    await expect(
      page.getByText("No rows exist in the runs table yet. No figures are rendered before then.", {
        exact: true,
      }),
    ).toBeVisible();
    // Also check for the Database icon? We can check for an aria-hidden icon from lucide, but it's not straightforward.
    // We'll rely on the text.
  });

  test("shows error state when state=error", async ({ page }) => {
    await page.goto("/runs?state=error");
    // Check for ErrorState: from page-states.tsx, ErrorState renders:
    // <TriangleAlert className="size-5 text-destructive" aria-hidden="true" />
    // <div className="text-sm font-medium text-foreground">{title}</div>
    // <p className="max-w-md text-sm text-muted-foreground">{detail}</p>
    // For Runs route, errorTitle="Run index unavailable", errorDetail="The data source did not respond. Nothing is displayed rather than a stale or synthetic figure."
    await expect(page.getByText("Run index unavailable", { exact: true })).toBeVisible();
    await expect(
      page.getByText(
        "The data source did not respond. Nothing is displayed rather than a stale or synthetic figure.",
        { exact: true },
      ),
    ).toBeVisible();
  });
});
