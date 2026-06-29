/**
 * Extract FSA (first 3 chars) from a Canadian postal code or address string.
 * Accepts "M5H 2N2", "M5H2N2", or full addresses containing a postal code.
 */
export function extractFsa(input: string): string | null {
  const normalized = input.toUpperCase().replace(/\s+/g, " ").trim();
  const fullMatch = normalized.match(/\b([A-Z]\d[A-Z])\s?(\d[A-Z]\d)\b/);
  if (fullMatch) return fullMatch[1];
  const fsaOnly = normalized.match(/\b([A-Z]\d[A-Z])\b/);
  return fsaOnly ? fsaOnly[1] : null;
}

export function normalizePostalCodes(codes: string[]): string[] {
  const fsas = new Set<string>();
  for (const code of codes) {
    const fsa = extractFsa(code);
    if (fsa) fsas.add(fsa);
  }
  return [...fsas];
}
