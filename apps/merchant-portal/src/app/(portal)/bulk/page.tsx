"use client";

import Button from "@/components/ui/Button";
import { BulkErrorReport, BulkPreviewTable } from "@/components/bulk/BulkUploadReport";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import {
  confirmBulk,
  confirmRouteImport,
  optimizeRouteImport,
  patchRouteImportMapping,
  patchRouteImportStop,
  saveRouteImportMappingProfile,
  uploadBulkCsv,
  uploadRouteImport,
  type RouteImportJob,
} from "@/lib/api";
import { DateTimePickerSeparateField } from "@porterchain/ui/datetime-picker-separate";
import { Download } from "lucide-react";
import { useEffect, useState } from "react";

const SAMPLE_CSV_URL = "/samples/bulk-bookings-sample.csv";
const ROUTE_SAMPLE_CSV_URL = "/samples/route-import-sample.csv";
const VEHICLES = ["sedan", "suv", "pickup", "cargoVan", "highRoof", "box16", "box20"];
const MAP_FIELDS = [
  "address",
  "unit",
  "city",
  "province",
  "postal",
  "stop_type",
  "sequence",
  "contact_name",
  "contact_phone",
  "external_ref",
  "lat",
  "lng",
  "notes",
] as const;

type Tab = "route" | "classic";
type MappingRow = { canonical: string; source: string | null; confidence?: number };

export default function BulkPage() {
  const { getApiToken, orgId, isSignedIn } = useMerchantAuth();
  const [tab, setTab] = useState<Tab>("route");

  const [preview, setPreview] = useState<{
    job_id: string;
    valid_rows: number;
    error_rows: number;
    duplicate_rows: number;
    preview: Array<Record<string, unknown>>;
    errors: Array<Record<string, unknown>>;
  } | null>(null);
  const [routeJob, setRouteJob] = useState<RouteImportJob | null>(null);
  const [vehicleClass, setVehicleClass] = useState("highRoof");
  const [scheduledAt, setScheduledAt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editAddress, setEditAddress] = useState("");
  const [draftMapping, setDraftMapping] = useState<MappingRow[]>([]);

  useEffect(() => {
    if (!routeJob?.mapping?.length) {
      setDraftMapping([]);
      return;
    }
    setDraftMapping(
      routeJob.mapping.map((m) => ({
        canonical: String(m.canonical ?? ""),
        source: m.source == null ? null : String(m.source),
        confidence: typeof m.confidence === "number" ? m.confidence : undefined,
      }))
    );
  }, [routeJob?.job_id, routeJob?.mapping]);

  async function onClassicUpload(e: React.ChangeEvent<HTMLInputElement>) {
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

  async function onClassicConfirm() {
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

  async function onRouteUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !isSignedIn) return;
    setLoading(true);
    setError(null);
    setConfirmed(false);
    setRouteJob(null);
    try {
      const token = await getApiToken();
      const job = await uploadRouteImport(token, file, {
        vehicleClass,
        scheduledAt: scheduledAt || undefined,
        orgId,
      });
      setRouteJob(job);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  async function onRouteConfirm() {
    if (!routeJob || !isSignedIn) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      const job = await confirmRouteImport(token, routeJob.job_id, orgId);
      setRouteJob(job);
      setConfirmed(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Confirm failed");
    } finally {
      setLoading(false);
    }
  }

  async function onOptimize() {
    if (!routeJob || !isSignedIn) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      setRouteJob(await optimizeRouteImport(token, routeJob.job_id, orgId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Optimize failed");
    } finally {
      setLoading(false);
    }
  }

  async function onSaveMapping() {
    if (!routeJob || !isSignedIn) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      const name = window.prompt("Name this column mapping", "My spreadsheet") || "My spreadsheet";
      await saveRouteImportMappingProfile(token, routeJob.job_id, name, orgId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save mapping failed");
    } finally {
      setLoading(false);
    }
  }

  async function onSaveStop() {
    if (editingIndex == null || !routeJob || !isSignedIn) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      const job = await patchRouteImportStop(
        token,
        routeJob.job_id,
        editingIndex,
        { address: editAddress },
        orgId
      );
      setRouteJob(job);
      setEditingIndex(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Address update failed");
    } finally {
      setLoading(false);
    }
  }

  async function onApplyMapping() {
    if (!routeJob || !isSignedIn || draftMapping.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      const job = await patchRouteImportMapping(token, routeJob.job_id, draftMapping, orgId);
      setRouteJob(job);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Mapping update failed");
    } finally {
      setLoading(false);
    }
  }

  const quoteReady = Boolean(routeJob?.quote?.amount_cents != null);
  const canConfirmRoute =
    quoteReady && (routeJob?.errors?.length ?? 0) === 0 && (routeJob?.stops?.length ?? 0) >= 2;
  const needsMappingReview =
    Boolean(routeJob?.errors?.some((e) => e.code === "mapping.address_low_confidence")) ||
    Boolean(
      draftMapping.some(
        (m) => m.canonical === "address" && (!m.source || (m.confidence ?? 0) < 0.8)
      )
    );
  const headerOptions = routeJob?.headers?.length
    ? routeJob.headers
    : Array.from(new Set(draftMapping.map((m) => m.source).filter((s): s is string => Boolean(s))));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Bulk &amp; route import</h1>
        <p className="text-sm text-muted">
          <span className="font-medium text-primary">Route import</span> — one multi-stop order (1
          pickup → many drops). <span className="font-medium text-primary">Classic bulk</span> —
          many separate A→B orders (one per CSV row). Book → Multiple deliveries is also N× separate
          orders, not one route.
        </p>
      </div>

      <div className="flex gap-2 border-b border-primary/10 pb-2">
        <button
          type="button"
          className={`rounded-lg px-4 py-2 text-sm font-medium ${
            tab === "route" ? "bg-primary text-white" : "text-primary hover:bg-gray-bg"
          }`}
          onClick={() => setTab("route")}
        >
          Route import
        </button>
        <button
          type="button"
          className={`rounded-lg px-4 py-2 text-sm font-medium ${
            tab === "classic" ? "bg-primary text-white" : "text-primary hover:bg-gray-bg"
          }`}
          onClick={() => setTab("classic")}
        >
          Classic bulk (legacy)
        </button>
      </div>

      {tab === "route" && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-primary/10 bg-white p-6 space-y-4">
            <p className="text-sm text-muted">
              Select vehicle once, then upload stops (CSV / XLSX). Addresses are cleaned and
              geocoded with Nominatim; quote uses Valhalla distance and GTA rates.
            </p>
            <div className="flex flex-wrap items-end gap-4">
              <label className="text-sm">
                <span className="mb-1 block font-medium text-primary">Vehicle</span>
                <select
                  className="rounded-xl border border-primary/15 px-3 py-2"
                  value={vehicleClass}
                  onChange={(e) => setVehicleClass(e.target.value)}
                >
                  {VEHICLES.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              </label>
              <div className="text-sm">
                <span className="mb-1 block font-medium text-primary">Scheduled at (optional)</span>
                <DateTimePickerSeparateField
                  value={scheduledAt}
                  onChange={setScheduledAt}
                  hourFormat={12}
                  timeInterval={15}
                  minDate={new Date()}
                  datePlaceholder="Pick a date"
                  timePlaceholder="Pick time"
                />
              </div>
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={onRouteUpload}
                disabled={loading}
              />
              <a
                href={ROUTE_SAMPLE_CSV_URL}
                download="route-import-sample.csv"
                className="inline-flex items-center gap-2 rounded-xl border border-primary/15 px-4 py-2 text-sm font-medium text-primary transition hover:bg-gray-bg"
              >
                <Download className="h-4 w-4" />
                Sample route CSV
              </a>
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>

          {routeJob && (
            <div className="space-y-4 rounded-2xl border border-primary/10 bg-white p-6">
              <p className="text-sm text-muted">{routeJob.route_explanation}</p>
              {routeJob.quote ? (
                <div className="rounded-xl bg-gray-bg/60 px-4 py-3 text-sm">
                  <p className="font-medium text-primary">
                    Quote: ${((routeJob.quote.amount_cents ?? 0) / 100).toFixed(2)}{" "}
                    {routeJob.quote.currency?.toUpperCase() || "CAD"}
                  </p>
                  <p className="text-muted">
                    Distance:{" "}
                    {routeJob.quote.distance_meters != null
                      ? `${(routeJob.quote.distance_meters / 1000).toFixed(1)} km`
                      : "—"}{" "}
                    · Source: {routeJob.quote.routing_source || "—"} · Drops:{" "}
                    {routeJob.quote.total_drops ?? "—"}
                  </p>
                </div>
              ) : (
                <p className="text-sm text-amber-700">
                  Quote unavailable until every stop geocodes successfully. Fix addresses below.
                </p>
              )}

              {routeJob.errors.length > 0 && (
                <div>
                  <h3 className="font-medium text-primary">Issues</h3>
                  <pre className="mt-2 overflow-auto rounded-lg bg-red-50 p-3 text-xs text-red-800">
                    {JSON.stringify(routeJob.errors, null, 2)}
                  </pre>
                </div>
              )}

              {draftMapping.length > 0 && (
                <div className="rounded-xl border border-primary/10 p-4 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-medium text-primary">Column mapping</h3>
                    {needsMappingReview && (
                      <span className="text-xs text-amber-700">
                        Address mapping needs review before quote
                      </span>
                    )}
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {MAP_FIELDS.map((field) => {
                      const row = draftMapping.find((m) => m.canonical === field);
                      return (
                        <label key={field} className="text-sm">
                          <span className="mb-1 block text-muted">{field}</span>
                          <select
                            className="w-full rounded-xl border border-primary/15 px-3 py-2"
                            value={row?.source ?? ""}
                            onChange={(e) => {
                              const source = e.target.value || null;
                              setDraftMapping((prev) => {
                                const next = prev.filter((m) => m.canonical !== field);
                                next.push({
                                  canonical: field,
                                  source,
                                  confidence: source ? 1 : 0,
                                });
                                return next;
                              });
                            }}
                          >
                            <option value="">— ignore —</option>
                            {headerOptions.map((h) => (
                              <option key={h} value={h}>
                                {h}
                              </option>
                            ))}
                          </select>
                        </label>
                      );
                    })}
                  </div>
                  <Button variant="outline" onClick={onApplyMapping} disabled={loading}>
                    Apply mapping &amp; re-quote
                  </Button>
                </div>
              )}

              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-primary/10 text-muted">
                      <th className="py-2 pr-3">#</th>
                      <th className="py-2 pr-3">Type</th>
                      <th className="py-2 pr-3">Address</th>
                      <th className="py-2 pr-3">Unit</th>
                      <th className="py-2 pr-3">Geo</th>
                      <th className="py-2">Fix</th>
                    </tr>
                  </thead>
                  <tbody>
                    {routeJob.stops.map((stop, idx) => (
                      <tr key={idx} className="border-b border-primary/5">
                        <td className="py-2 pr-3">{String(stop.sequence ?? idx + 1)}</td>
                        <td className="py-2 pr-3">{String(stop.stop_type ?? "")}</td>
                        <td className="py-2 pr-3 max-w-md truncate">
                          {String(stop.formatted || stop.raw_address || stop.address || "")}
                        </td>
                        <td className="py-2 pr-3">{String(stop.unit ?? "—")}</td>
                        <td className="py-2 pr-3">{String(stop.geocode_status ?? "")}</td>
                        <td className="py-2">
                          <button
                            type="button"
                            className="text-primary underline"
                            onClick={() => {
                              setEditingIndex(idx);
                              setEditAddress(
                                String(stop.raw_address || stop.address || stop.formatted || "")
                              );
                            }}
                          >
                            Edit
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {editingIndex != null && (
                <div className="flex flex-wrap items-end gap-2 rounded-xl border border-primary/10 p-3">
                  <label className="flex-1 text-sm">
                    <span className="mb-1 block font-medium">Stop {editingIndex + 1} address</span>
                    <input
                      className="w-full rounded-xl border border-primary/15 px-3 py-2"
                      value={editAddress}
                      onChange={(e) => setEditAddress(e.target.value)}
                    />
                  </label>
                  <Button onClick={onSaveStop} disabled={loading}>
                    Re-geocode
                  </Button>
                  <Button variant="secondary" onClick={() => setEditingIndex(null)}>
                    Cancel
                  </Button>
                </div>
              )}

              {routeJob.route_geometry?.polyline && (
                <p className="text-xs text-muted">
                  Route geometry ready ({routeJob.route_geometry.leg_count ?? "multi"} legs via{" "}
                  {routeJob.route_geometry.source || "valhalla"}
                  {routeJob.optimized ? " · optimized order" : ""}).
                </p>
              )}

              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={onOptimize} disabled={loading || !quoteReady}>
                  Optimize drop order
                </Button>
                {(routeJob.mapping?.length ?? 0) > 0 && (
                  <Button variant="ghost" onClick={onSaveMapping} disabled={loading}>
                    Save column mapping
                  </Button>
                )}
                {!confirmed ? (
                  <Button onClick={onRouteConfirm} disabled={loading || !canConfirmRoute}>
                    Confirm route booking
                  </Button>
                ) : (
                  <p className="text-sm font-medium text-green-700 self-center">
                    Route booked
                    {routeJob.order_ids?.[0] ? ` · order ${routeJob.order_ids[0]}` : ""}.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "classic" && (
        <>
          <div className="rounded-2xl border border-primary/10 bg-white p-6">
            <p className="mb-3 text-sm text-muted">
              Legacy: one A→B order per CSV row. Prefer Route import for multi-stop jobs.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <input
                type="file"
                accept=".csv,.xlsx"
                onChange={onClassicUpload}
                disabled={loading}
              />
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
                <Button onClick={onClassicConfirm} disabled={loading || preview.valid_rows === 0}>
                  Confirm bulk import
                </Button>
              ) : (
                <p className="text-sm font-medium text-green-700">
                  Bulk bookings confirmed and dispatched.
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
