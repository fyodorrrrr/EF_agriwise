export function normalizePsgcCode(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const digits = String(value).trim().toUpperCase().replace(/^PH/, "").replace(/\D/g, "");
  return digits || null;
}
