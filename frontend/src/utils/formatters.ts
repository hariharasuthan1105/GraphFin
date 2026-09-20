/**
 * Currency locale map for Intl.NumberFormat.
 * Maps ISO 4217 codes to the most appropriate BCP-47 locale:
 *   - INR uses 'en-IN' to get correct Indian digit grouping
 *     (lakhs/crores: ₹1,00,000 not ₹100,000)
 *   - USD uses 'en-US', GBP uses 'en-GB', EUR uses 'en-IE'
 * Add more entries here as new currencies are supported.
 */
const CURRENCY_LOCALE_MAP: Record<string, string> = {
  USD: "en-US",
  INR: "en-IN",
  EUR: "en-IE",
  GBP: "en-GB",
};

/** Resolve the best locale for a given ISO 4217 currency code. */
function localeForCurrency(code: string): string {
  return CURRENCY_LOCALE_MAP[code?.toUpperCase()] ?? "en-US";
}

/**
 * Format a monetary amount using the given ISO 4217 currency code.
 * Uses browser-native Intl.NumberFormat — no external library required.
 *
 * Examples:
 *   formatCurrency(100000, "INR") → "₹1,00,000.00"   (Indian grouping)
 *   formatCurrency(100000, "USD") → "$100,000.00"
 *   formatCurrency(100000, "EUR") → "€100,000.00"
 *   formatCurrency(100000, "GBP") → "£100,000.00"
 */
export function formatCurrency(amount: number, currency = "USD"): string {
  const code = (currency ?? "USD").toUpperCase();
  return new Intl.NumberFormat(localeForCurrency(code), {
    style: "currency",
    currency: code,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/**
 * Create a bound currency formatter for a fixed currency code.
 * Use this in components that read currency from context once and
 * need to call the formatter many times in a render:
 *
 *   const fmt = makeCurrencyFormatter(datasetCurrency);
 *   fmt(amount); // always uses the bound currency
 */
export function makeCurrencyFormatter(currency = "USD"): (amount: number) => string {
  const code = (currency ?? "USD").toUpperCase();
  const locale = localeForCurrency(code);
  const formatter = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: code,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return (amount: number) => formatter.format(amount);
}

export function formatNumber(val: number, decimals = 0): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(val);
}

export function formatPercent(val: number, decimals = 1): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  return `${(val * 100).toFixed(decimals)}%`;
}

export function formatMetric(val: number | null | undefined, decimals = 4): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  return val.toFixed(decimals);
}

export function truncateId(id: string, startChars = 8, endChars = 4): string {
  if (!id) return "";
  if (id.length <= startChars + endChars) return id;
  return `${id.slice(0, startChars)}...${id.slice(-endChars)}`;
}
