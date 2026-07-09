"use client";

import Button from "@/components/ui/Button";
import { BulkErrorReport, BulkPreviewTable } from "@/components/bulk/BulkUploadReport";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { confirmBulk, uploadBulkCsv } from "@/lib/api";
import { Download } from "lucide-react";
import { useState } from "react";

const SAMPLE_CSV_URL = "/samples/bulk-bookings-sample.csv";

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
          Upload CSV or Excel (.xlsx) with columns: pickup, dropoff, scheduled_at (optional:
          internal_reference, purchase_order_number, cost_centre, pickup_lat, pickup_lng,
          dropoff_lat, dropoff_lng, recipient_id, vehicle_class, package_type, weight_kg)
        </p>
      </div>

      <div className="rounded-2xl border border-primary/10 bg-white p-6">
        <div className="flex flex-wrap items-center gap-3">
          <input type="file" accept=".csv,.xlsx" onChange={onUpload} disabled={loading} />
          <a
            href={SAMPLE_CSV_URL}
            download="bulk-bookings-sample.csv"
            className="inline-flex items-center gap-2 rounded-xl border border-primary/15 px-4 py-2 text-sm font-medium text-primary transition hover:bg-gray-bg"
          >
            <Download className="h-4 w-4" />
            Download sample CSV
          </a>
        </div>
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
              <div className="mt-2">
                <BulkErrorReport errors={preview.errors} />
              </div>
            </div>
          )}
          {preview.preview.length > 0 && (
            <div>
              <h3 className="font-medium text-primary">Preview</h3>
              <div className="mt-2">
                <BulkPreviewTable rows={preview.preview} />
              </div>
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
