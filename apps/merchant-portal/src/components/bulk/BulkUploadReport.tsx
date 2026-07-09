type BulkError = Record<string, unknown>;

const ERROR_LABELS: Record<string, string> = {
  duplicate: "Duplicate row (same pickup, drop-off, and schedule as another row)",
  address_validation: "Invalid pickup or drop-off address",
  recipient_not_found: "Recipient ID not found in your account",
  invalid_scheduled_at: "Scheduled time is missing or invalid (use ISO format)",
  missing_columns: "Required columns missing from file",
};

function formatBulkError(err: BulkError): string {
  const code = String(err.error ?? "unknown");
  if (code.startsWith("missing_columns:")) {
    const cols = code.replace("missing_columns:", "");
    return `Missing required columns: ${cols}`;
  }
  const base = ERROR_LABELS[code] ?? code.replace(/_/g, " ");
  const details = err.details;
  if (details && typeof details === "object") {
    const parts = Object.entries(details as Record<string, string>)
      .map(([k, v]) => `${k}: ${v}`)
      .join("; ");
    if (parts) return `${base} (${parts})`;
  }
  if (err.recipient_id) return `${base} (recipient: ${String(err.recipient_id)})`;
  return base;
}

export function BulkErrorReport({ errors }: { errors: BulkError[] }) {
  if (!errors.length) return null;

  return (
    <div className="overflow-hidden rounded-xl border border-red-200 bg-red-50/60">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-red-200/80 bg-red-100/50">
            <th className="px-3 py-2 font-semibold text-red-900">Row</th>
            <th className="px-3 py-2 font-semibold text-red-900">Issue</th>
          </tr>
        </thead>
        <tbody>
          {errors.slice(0, 50).map((err, idx) => (
            <tr key={`${String(err.row)}-${idx}`} className="border-b border-red-100 last:border-0">
              <td className="px-3 py-2 font-mono text-red-800">{String(err.row ?? "—")}</td>
              <td className="px-3 py-2 text-red-900">{formatBulkError(err)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {errors.length > 50 && (
        <p className="px-3 py-2 text-xs text-red-700">
          Showing first 50 of {errors.length} errors.
        </p>
      )}
    </div>
  );
}

export function BulkPreviewTable({ rows }: { rows: Array<Record<string, unknown>> }) {
  if (!rows.length) return null;
  const columns = Object.keys(rows[0] ?? {}).slice(0, 8);

  return (
    <div className="overflow-x-auto rounded-xl border border-primary/10">
      <table className="min-w-full text-left text-xs">
        <thead>
          <tr className="border-b border-primary/10 bg-gray-bg">
            {columns.map((col) => (
              <th key={col} className="px-3 py-2 font-semibold text-primary">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 10).map((row, idx) => (
            <tr key={idx} className="border-b border-primary/5 last:border-0">
              {columns.map((col) => (
                <td key={col} className="max-w-[180px] truncate px-3 py-2 text-muted">
                  {String(row[col] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
