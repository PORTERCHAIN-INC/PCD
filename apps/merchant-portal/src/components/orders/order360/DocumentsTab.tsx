"use client";

import Button from "@/components/ui/Button";
import type { OrderDetail } from "@/lib/orders";
import { Card } from "./shared";

export function DocumentsTab({
  documents,
  onDownloadRecord,
  onPrintLabels,
  onPrintPreview,
  busy,
  printBusy,
  error,
}: {
  documents: Array<Record<string, unknown>>;
  onDownloadRecord: () => void;
  onPrintLabels: () => void;
  onPrintPreview: () => void;
  busy: boolean;
  printBusy: boolean;
  error: string | null;
}) {
  return (
    <Card title="Documents">
      <div className="mb-4 space-y-2 border-b border-primary/10 pb-4">
        <p className="text-sm text-muted">
          Download a shipment record: addresses, references, stops, and the activity trail.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={onPrintLabels} disabled={printBusy}>
            {printBusy ? "Preparing…" : "Print labels (4×6)"}
          </Button>
          <Button size="sm" variant="outline" onClick={onDownloadRecord} disabled={busy}>
            {busy ? "Downloading…" : "Download shipment record"}
          </Button>
          <Button size="sm" variant="outline" onClick={onPrintPreview} disabled={printBusy}>
            {printBusy ? "Preparing…" : "Dock sheet"}
          </Button>
        </div>
        <p className="text-xs text-muted">
          Labels are one 4×6 page per box (QR). Dock sheet is addresses only — not a carrier label.
        </p>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
      </div>
      {documents.length === 0 ? (
        <p className="text-muted">No other files attached to this order.</p>
      ) : (
        <ul className="space-y-2">
          {documents.map((d, i) => (
            <li key={i}>
              <a
                href={String(d.url)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-secondary hover:underline"
              >
                {String(d.name ?? d.type)}
              </a>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
