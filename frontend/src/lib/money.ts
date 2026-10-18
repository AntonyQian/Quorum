/** Format integer cents as dollars. Money stays in cents everywhere else. */
export function formatCents(cents: number): string {
  const negative = cents < 0;
  const absolute = Math.abs(cents);
  const dollars = Math.floor(absolute / 100);
  const remainder = absolute % 100;
  const formatted = `$${dollars.toLocaleString("en-US")}.${remainder.toString().padStart(2, "0")}`;
  return negative ? `-${formatted}` : formatted;
}

/** Parse a dollars text field ("12.50") into integer cents; null when blank or not a number. */
export function dollarsToCents(text: string): number | null {
  const trimmed = text.trim();
  if (!/^\d+(\.\d{0,2})?$/.test(trimmed)) return null;
  return Math.round(Number(trimmed) * 100);
}
