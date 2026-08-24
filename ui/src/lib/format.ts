/**
 * Display-layer formatting only. Money is carried as integer paise everywhere
 * in the app and never converted until it is rendered.
 */

const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const inrCompact = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  notation: "compact",
  maximumFractionDigits: 2,
});

const integer = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

/** Integer paise -> "₹1,23,456.78". */
export function formatPaise(paise: number): string {
  return inr.format(paise / 100);
}

/** Integer paise -> "₹1.23L" for dense table cells. */
export function formatPaiseCompact(paise: number): string {
  return inrCompact.format(paise / 100);
}

export function formatCount(value: number): string {
  return integer.format(value);
}

/**
 * A rate is never rendered alone: callers must always surface the numerator
 * and denominator alongside the percentage.
 */
export function formatRate(numerator: number, denominator: number, digits = 2): string {
  if (denominator === 0) return "—";
  return `${((numerator / denominator) * 100).toFixed(digits)}%`;
}
