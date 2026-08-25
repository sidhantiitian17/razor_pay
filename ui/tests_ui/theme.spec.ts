import { test, expect } from "@playwright/test";

// Helper to calculate luminance from an RGB color string (e.g., "rgb(255, 255, 255)" or "#ffffff")
function luminance(color: string): number {
  // Convert color to RGB array [r, g, b] in range 0-255
  let r: number, g: number, b: number;
  if (color.startsWith("rgb(")) {
    const match = color.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
    if (!match) throw new Error(`Invalid rgb color: ${color}`);
    r = parseInt(match[1], 10);
    g = parseInt(match[2], 10);
    b = parseInt(match[3], 10);
  } else if (color.startsWith("#") && color.length === 7) {
    r = parseInt(color.slice(1, 3), 16);
    g = parseInt(color.slice(3, 5), 16);
    b = parseInt(color.slice(5, 7), 16);
  } else if (color.startsWith("oklch(")) {
    // Chromium's getComputedStyle serializes CSS Color 4 values (Tailwind v4's
    // default palette) as oklch(), not rgb() -- convert via OKLab to linear
    // sRGB per the CSS Color 4 spec, then use the linear components directly
    // (skip the gamma-decode step below, which assumes gamma-encoded input).
    const match = color.match(/oklch\(([\d.]+)\s+([\d.]+)\s+([\d.]+)/);
    if (!match) throw new Error(`Invalid oklch color: ${color}`);
    const [L, C, H] = [parseFloat(match[1]), parseFloat(match[2]), parseFloat(match[3])];
    const hRad = (H * Math.PI) / 180;
    const a = C * Math.cos(hRad);
    const bLab = C * Math.sin(hRad);

    const l_ = L + 0.3963377774 * a + 0.2158037573 * bLab;
    const m_ = L - 0.1055613458 * a - 0.0638541728 * bLab;
    const s_ = L - 0.0894841775 * a - 1.291485548 * bLab;
    const l = l_ ** 3;
    const m = m_ ** 3;
    const s = s_ ** 3;

    const rLin = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s;
    const gLin = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s;
    const bLin = -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s;
    const clamp = (v: number) => Math.min(1, Math.max(0, v));
    return 0.2126 * clamp(rLin) + 0.7152 * clamp(gLin) + 0.0722 * clamp(bLin);
  } else {
    // Assume it's a CSS variable or named color; we cannot compute, so return a default that will fail the test if used.
    // For simplicity, we treat unknown colors as black, which will likely cause a failure if present.
    return 0;
  }
  // Convert to sRGB and normalize to 0-1
  const [rs, gs, bs] = [r, g, b].map((v) => {
    const vNorm = v / 255;
    return vNorm <= 0.03928 ? vNorm / 12.92 : Math.pow((vNorm + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

// Helper to calculate contrast ratio between two colors
function contrastRatio(color1: string, color2: string): number {
  const lum1 = luminance(color1);
  const lum2 = luminance(color2);
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

test.describe("Theme", () => {
  test("both themes render and have sufficient contrast", async ({ page }) => {
    // Test light theme
    await page.goto("/");
    await page.emulateMedia({ colorScheme: "light" });
    await page.reload();
    // Wait for theme to apply
    await page.waitForFunction(() => document.documentElement.classList.contains("dark") === false);
    const isDark = await page.evaluate(() => document.documentElement.classList.contains("dark"));
    expect(isDark).toBe(false);

    // Check contrast for a sample of text elements
    await checkContrast(page);

    // Test dark theme
    await page.emulateMedia({ colorScheme: "dark" });
    await page.reload();
    await page.waitForFunction(() => document.documentElement.classList.contains("dark") === true);
    const isDark2 = await page.evaluate(() => document.documentElement.classList.contains("dark"));
    expect(isDark2).toBe(true);

    await checkContrast(page);
  });
});

async function checkContrast(page: import("@playwright/test").Page) {
  // Get all text elements that are visible and have a foreground color
  // We'll query for common text elements: h1, h2, h3, p, span, div (but only those that are likely to contain text)
  // To avoid too many elements, we'll limit to a few selectors.
  const selectors = [
    "h1, h2, h3, h4, h5, h6",
    "p",
    "span",
    'div[class*="text-"]', // heuristic for text elements
    "button",
    "label",
    "li",
  ];
  const elements = await page.locator(selectors.join(",")).all();
  // Limit to first 20 elements to avoid slowness
  const limited = elements.slice(0, 20);
  for (const element of limited) {
    if (!(await element.isVisible())) continue;
    const info = await element.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        ariaHidden: el.getAttribute("aria-hidden"),
        text: el.textContent?.trim() ?? "",
        color: style.color,
        backgroundColor: style.backgroundColor,
      };
    });
    // WCAG 1.4.3 contrast applies to text (and images of text), not decorative
    // non-text nodes. Skip aria-hidden elements and elements with no rendered
    // text -- e.g. a filled status dot -- since there is no glyph for the
    // reader to fail to perceive, so the element's inherited `color` is
    // irrelevant regardless of how it measures against its background.
    if (info.ariaHidden === "true" || info.text.length === 0) continue;
    const { color, backgroundColor } = info;
    // Skip if background is transparent or if we cannot compute
    if (backgroundColor === "transparent" || backgroundColor === "rgba(0, 0, 0, 0)") {
      // We need to get the background color of the parent? Too complex.
      // For now, we skip transparent backgrounds.
      continue;
    }
    let ratio: number;
    try {
      ratio = contrastRatio(color, backgroundColor);
    } catch (e) {
      // If we cannot compute contrast, fail loudly rather than silently skip.
      throw new Error(`Could not compute contrast for element: ${e}`);
    }
    expect(
      ratio,
      `Element has insufficient contrast: ${color} on ${backgroundColor} ratio=${ratio}`,
    ).toBeGreaterThanOrEqual(4.5);
  }
}
