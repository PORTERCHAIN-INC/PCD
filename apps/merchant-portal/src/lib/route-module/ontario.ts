/** Ontario forward sortation areas used by PorterChain GTA / Ontario routing. */
const ONTARIO_POSTAL = /^[KLMNP]\d[A-Z]\s?\d[A-Z]\d$/i;

export function normalizePostal(value: string): string {
  return value.replace(/\s+/g, "").toUpperCase();
}

export function formatOntarioPostal(value: string): string {
  const compact = normalizePostal(value);
  if (compact.length !== 6) return value.trim().toUpperCase();
  return `${compact.slice(0, 3)} ${compact.slice(3)}`;
}

export function isOntarioPostal(value: string | undefined | null): boolean {
  if (!value) return false;
  return ONTARIO_POSTAL.test(value.trim());
}

export function postalFromAddress(address: string, explicit?: string): string {
  if (explicit && isOntarioPostal(explicit)) return formatOntarioPostal(explicit);
  const match = address.toUpperCase().match(/\b([KLMNP]\d[A-Z])\s?(\d[A-Z]\d)\b/);
  if (!match) return explicit?.trim() ?? "";
  return `${match[1]} ${match[2]}`;
}

export function isOntarioProvince(value: string | undefined | null): boolean {
  if (!value || !value.trim()) return true;
  const normalized = value.trim().toLowerCase();
  return normalized === "on" || normalized === "ontario";
}
