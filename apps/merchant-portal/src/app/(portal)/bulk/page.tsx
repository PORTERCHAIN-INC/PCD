"use client";

import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { confirmBulk, uploadBulkCsv } from "@/lib/api";
import { useState } from "react";

export default function BulkPage() {
  const { getApiToken, orgId, isSignedIn } = useMerchantAuth();
  const [preview, setPreview] = useState<{
    job_id: string;
    valid_rows: number;
    error_rows: number;
    duplicate_rows: number;
    preview: Array<Record<string, unknown>>;
    errors: Array<Record<string, unknown>>;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !isSignedIn) return;
    setLoading(true);
    setError(null);
    setConfirmed(false);
    try {
      const token = await getApiToken();
      const job = await uploadBulkCsv(token, file, orgId);
      setPreview(job);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  async function onConfirm() {
    if (!preview || !isSignedIn) return;
    setLoading(true);
    try {
      const token = await getApiToken();
      await confirmBulk(token, preview.job_id, orgId);
      setConfirmed(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Confirm failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Bulk Bookings</h1>
        <p className="text-sm text-muted">
          Upload CSV with columns: pickup, dropoff, scheduled_at (optional: internal_reference,
          purchase_order_number, cost_centre)
        </p>
      </div>

      <div className="rounded-2xl border border-primary/10 bg-white p-6">
        <input type="file" accept=".csv,.xlsx" onChange={onUpload} disabled={loading} />
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </div>

      {preview && (
        <div className="space-y-4 rounded-2xl border border-primary/10 bg-white p-6">
          <p className="text-sm">
            Valid: {preview.valid_rows} · Errors: {preview.error_rows} · Duplicates:{" "}
            {preview.duplicate_rows}
          </p>
          {preview.errors.length > 0 && (
            <div>
              <h3 className="font-medium text-primary">Error report</h3>
              <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-gray-bg p-3 text-xs">
                {JSON.stringify(preview.errors, null, 2)}
              </pre>
            </div>
          )}
          {preview.preview.length > 0 && (
            <div>
              <h3 className="font-medium text-primary">Preview</h3>
              <pre className="mt-2 max-h-60 overflow-auto rounded-lg bg-gray-bg p-3 text-xs">
                {JSON.stringify(preview.preview.slice(0, 10), null, 2)}
              </pre>
            </div>
          )}
          {!confirmed ? (
            <Button onClick={onConfirm} disabled={loading || preview.valid_rows === 0}>
              Confirm bulk import
            </Button>
          ) : (
            <p className="text-sm font-medium text-green-700">
              Bulk bookings confirmed and dispatched.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
