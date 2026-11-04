/** Doc 72: HST is stored as its own `hst` line. Views that print Subtotal/HST/Total rows
 *  render it once in the HST row, never again among the pre-tax lines. */
export type HstSplitLine = { code?: string | null; amount_cents?: number | null };

export function splitHstLine<T extends HstSplitLine>(
  lines: T[]
): { pretax: T[]; hstCents: number | null } {
  const isHst = (l: T) => String(l.code ?? "").toLowerCase() === "hst";
  const hst = lines.filter(isHst);
  return {
    pretax: lines.filter((l) => !isHst(l)),
    hstCents: hst.length ? hst.reduce((a, l) => a + Number(l.amount_cents ?? 0), 0) : null,
  };
}
