"use client";

import { formatCents } from "./utils";

export type QuoteLine = {
  code?: string | null;
  label?: string | null;
  amount_cents?: number | null;
};

export type QuotePicture = {
  items?: QuoteLine[];
  line_items?: QuoteLine[];
  summary?: {
    items?: QuoteLine[];
    subtotal_cents?: number | null;
    tax_cents?: number | null;
    final_cents?: number | null;
  };
  subtotal_cents?: number | null;
  tax_cents?: number | null;
  final_cents?: number | null;
  amount_cents?: number | null;
  currency?: string | null;
  distance_meters?: number | null;
};

function asPicture(value: QuotePicture | Record<string, unknown> | null | undefined): QuotePicture {
  return (value ?? {}) as QuotePicture;
}

export function quoteLines(
  picture: QuotePicture | Record<string, unknown> | null | undefined
): QuoteLine[] {
  const raw = asPicture(picture);
  const nested = raw.summary?.items ?? [];
  const items = raw.items ?? raw.line_items ?? nested ?? [];
  return items.filter((i) => i && i.amount_cents != null);
}

type Props = {
  breakdown?: QuotePicture | Record<string, unknown> | null;
  quotedCents?: number | null;
  chargedCents?: number | null;
  currency?: string;
};

export function QuoteLines({ breakdown, quotedCents, chargedCents, currency = "CAD" }: Props) {
  const lines = quoteLines(breakdown);
  const picture = asPicture(breakdown);
  const nested = picture.summary ?? {};
  const subtotal = picture.subtotal_cents ?? nested.subtotal_cents;
  const tax = picture.tax_cents ?? nested.tax_cents;
  const total =
    picture.final_cents ??
    picture.amount_cents ??
    nested.final_cents ??
    quotedCents ??
    chargedCents;
  const quoted = quotedCents ?? picture.final_cents ?? picture.amount_cents ?? nested.final_cents;
  const charged = chargedCents;
  const showCompare = quoted != null && charged != null && quoted !== charged;

  return (
    <div className="space-y-2 text-sm">
      {lines.length > 0 ? (
        <ul className="space-y-1">
          {lines.map((line, i) => (
            <li key={`${line.code ?? line.label ?? i}`} className="flex justify-between gap-4">
              <span className="text-muted">{line.label || line.code || "Charge"}</span>
              <span>{formatCents(Number(line.amount_cents), currency)}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-muted">No line items on this quote.</p>
      )}
      {subtotal != null && (
        <p className="flex justify-between gap-4 border-t border-primary/10 pt-2">
          <span className="text-muted">Subtotal</span>
          <span>{formatCents(subtotal, currency)}</span>
        </p>
      )}
      {tax != null && (
        <p className="flex justify-between gap-4">
          <span className="text-muted">HST</span>
          <span>{formatCents(tax, currency)}</span>
        </p>
      )}
      {total != null && (
        <p className="flex justify-between gap-4 font-semibold text-primary">
          <span>Total</span>
          <span>{formatCents(total, currency)}</span>
        </p>
      )}
      {showCompare && (
        <div className="rounded-lg bg-amber-50 px-3 py-2 text-amber-900">
          <p>Quoted: {formatCents(quoted, currency)}</p>
          <p className="mt-0.5">Charged: {formatCents(charged, currency)}</p>
        </div>
      )}
    </div>
  );
}
