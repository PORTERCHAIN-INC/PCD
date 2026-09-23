"use client";

import Button from "@/components/ui/Button";
import { BulkErrorReport, BulkPreviewTable } from "@/components/bulk/BulkUploadReport";
import { QuoteLines } from "@/components/billing/QuoteLines";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import {
  applyRouteImportMappingProfile,
  confirmBulk,
  confirmRouteImport,
  listRouteImportMappingProfiles,
  optimizeRouteImport,
  patchRouteImportMapping,
  patchRouteImportStop,
  saveRouteImportMappingProfile,
  getRouteImport,
  uploadBulkCsv,
  uploadRouteImport,
  type RouteImportJob,
  type RouteImportMappingProfile,
} from "@/lib/api";
import { VEHICLE_OPTIONS, vehicleLabel } from "@/lib/catalog";
import { publicEnv } from "@/lib/env";
import { AddressAutocompleteInput, type BookingAddress } from "@porterchain/maps";
import { DateTimePickerSeparateField } from "@porterchain/ui/datetime-picker-separate";
import { Download } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

const SAMPLE_CSV_URL = "/samples/bulk-bookings-sample.csv";
const ROUTE_SAMPLE_CSV_URL = "/samples/route-import-sample.csv";
const VEHICLES = VEHICLE_OPTIONS.map((v) => v.id);
const MAP_FIELDS = [
  "pickup_address",
  "dropoff_address",
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
  "sku",
  "length",
  "width",
  "height",
  "dimensions_unit",
  "weight",
  "weight_unit",
  "quantity",
] as const;

type Tab = "route" | "classic";
type MappingRow = { canonical: string; source: string | null; confidence?: number };

/** Matches the API gate: one address column, or both pickup and dropoff columns. */
function addressMappingConfident(mapping: MappingRow[]): boolean {
  const confident = (field: string) =>
    mapping.some((m) => m.canonical === field && m.source && (m.confidence ?? 0) >= 0.8);
  return confident("address") || (confident("pickup_address") && confident("dropoff_address"));
}

export default function BulkPage() {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
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
  const [constructionSite, setConstructionSite] = useState(false);
  const [siteAccessNotes, setSiteAccessNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editAddress, setEditAddress] = useState("");
  /** Set when the merchant picks a Places suggestion — same shape as Book Delivery. */
  const [editPlace, setEditPlace] = useState<BookingAddress | null>(null);
  const [draftMapping, setDraftMapping] = useState<MappingRow[]>([]);
  const [profiles, setProfiles] = useState<RouteImportMappingProfile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [mappingName, setMappingName] = useState("My spreadsheet");

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

  const loadProfiles = useCallback(async () => {
    if (!isSignedIn || !orgId) return;
    const token = await getApiToken();
    const rows = await listRouteImportMappingProfiles(token, orgId);
    setProfiles(rows);
  }, [getApiToken, isSignedIn, orgId]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !orgId) return;
    void loadProfiles().catch(() => setProfiles([]));
  }, [isLoaded, isSignedIn, orgId, loadProfiles]);

  useEffect(() => {
    if (!routeJob || !isSignedIn || !orgId) return;
    const geoPending =
      routeJob.geocode === "pending" ||
      routeJob.stops.some((s) => String(s.geocode_status ?? "") === "pending");
    const optPending = routeJob.optimize_status === "pending";
    if (!geoPending && !optPending) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const token = await getApiToken();
        const job = await getRouteImport(token, routeJob.job_id, orgId);
        if (!cancelled) setRouteJob(job);
      } catch {
        /* keep last snapshot */
      }
    };
    const id = window.setInterval(() => void tick(), 1000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [
    getApiToken,
    isSignedIn,
    orgId,
    routeJob?.job_id,
    routeJob?.geocode,
    routeJob?.optimize_status,
    routeJob?.stops,
  ]);

  async function onClassicUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !isSignedIn || !orgId) return;
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
    if (!file || !isSignedIn || !orgId) return;
    setLoading(true);
    setError(null);
    setConfirmed(false);
    setRouteJob(null);
    try {
      const token = await getApiToken();
      const routeVehicle =
        constructionSite && ["sedan", "suv", "pickup"].includes(vehicleClass)
          ? "cargoVan"
          : vehicleClass;
      const job = await uploadRouteImport(token, file, {
        vehicleClass: routeVehicle,
        scheduledAt: scheduledAt || undefined,
        orgId,
        requiresLiftgate: constructionSite,
        siteAccessNotes: constructionSite
          ? ["Construction site", siteAccessNotes.trim()].filter(Boolean).join(". ")
          : undefined,
        mappingProfileId: selectedProfileId || undefined,
      });
      setRouteJob(job);
      if (job.mapping_profile_id) setSelectedProfileId(job.mapping_profile_id);
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
    setOptimizing(true);
    setError(null);
    try {
      const token = await getApiToken();
      setRouteJob(await optimizeRouteImport(token, routeJob.job_id, orgId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Optimize failed");
    } finally {
      setOptimizing(false);
    }
  }

  async function onSaveMapping() {
    if (!routeJob || !isSignedIn || !orgId) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      const saved = await saveRouteImportMappingProfile(
        token,
        routeJob.job_id,
        mappingName.trim() || "My spreadsheet",
        orgId
      );
      await loadProfiles();
      setSelectedProfileId(saved.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save that mapping.");
    } finally {
      setLoading(false);
    }
  }

  async function onLoadMapping() {
    if (!routeJob || !isSignedIn || !orgId || !selectedProfileId) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      setRouteJob(
        await applyRouteImportMappingProfile(token, routeJob.job_id, selectedProfileId, orgId)
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load that mapping.");
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
      // Places pick → lat/lng already known (Book Delivery path). Typed-only → Nominatim.
      const patch: Record<string, unknown> = {
        address: (editPlace?.formatted || editAddress).trim(),
      };
      if (editPlace?.lat != null && editPlace?.lng != null) {
        patch.lat = editPlace.lat;
        patch.lng = editPlace.lng;
        patch.geocode_source = "places";
        if (editPlace.placeId) patch.place_id = editPlace.placeId;
        if (editPlace.postal) patch.postal = editPlace.postal;
      }
      const job = await patchRouteImportStop(token, routeJob.job_id, editingIndex, patch, orgId);
      setRouteJob(job);
      setEditingIndex(null);
      setEditPlace(null);
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

  if (!isLoaded || !isSignedIn || !orgId) {
    return <p className="text-sm text-muted">Loading company…</p>;
  }

  const quoteReady = Boolean(routeJob?.quote?.amount_cents != null);
  const optimizePending = routeJob?.optimize_status === "pending";
  const quotedPreviewRow = preview?.preview.find((row) => row.pricing_breakdown);
  const canConfirmRoute =
    quoteReady &&
    !optimizePending &&
    (routeJob?.errors?.length ?? 0) === 0 &&
    (routeJob?.stops?.length ?? 0) >= 2;
  const needsMappingReview =
    Boolean(
      routeJob?.errors?.some(
        (e) =>
          e.code === "mapping.address_low_confidence" ||
          e.error === "mapping.address_low_confidence"
      )
    ) ||
    (draftMapping.length > 0 && !addressMappingConfident(draftMapping));
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
              Select vehicle once, then upload stops (CSV / XLSX). Repeat a sequence to add another
              parcel to that stop. Optional columns: length, width, height, dimensions_unit (cm, in,
              ft), weight, weight_unit (kg, lbs), sku, quantity. Confirm uses the same billing path
              as the route planner. Weight is recorded, not charged separately.
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
                      {vehicleLabel(v)}
                    </option>
                  ))}
                </select>
              </label>
              <div className="text-sm">
                <span className="mb-1 block font-medium text-primary">
                  Scheduled at (optional, America/Toronto)
                </span>
                <DateTimePickerSeparateField
                  value={scheduledAt}
                  onChange={setScheduledAt}
                  timezone="America/Toronto"
                  showTimezone={false}
                  hourFormat={12}
                  timeInterval={15}
                  minDate={new Date()}
                  datePlaceholder="Pick a date"
                  timePlaceholder="Pick time"
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-primary">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-primary/20"
                  checked={constructionSite}
                  onChange={(e) => setConstructionSite(e.target.checked)}
                />
                Construction site
              </label>
              {constructionSite ? (
                <input
                  className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
                  placeholder="Gate code, foreman, dock"
                  value={siteAccessNotes}
                  onChange={(e) => setSiteAccessNotes(e.target.value)}
                />
              ) : null}
              <label className="text-sm">
                <span className="mb-1 block font-medium text-primary">Saved mapping</span>
                <select
                  className="rounded-xl border border-primary/15 px-3 py-2"
                  value={selectedProfileId}
                  onChange={(e) => setSelectedProfileId(e.target.value)}
                >
                  <option value="">Guess columns</option>
                  {profiles.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>
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
                  {optimizePending ? (
                    <p className="font-medium text-primary">Updating price…</p>
                  ) : (
                    <p className="font-medium text-primary">
                      Quote: ${((routeJob.quote.amount_cents ?? 0) / 100).toFixed(2)}{" "}
                      {routeJob.quote.currency?.toUpperCase() || "CAD"}
                    </p>
                  )}
                  <p className="text-muted">
                    Distance:{" "}
                    {routeJob.quote.distance_meters != null
                      ? `${(routeJob.quote.distance_meters / 1000).toFixed(1)} km`
                      : "—"}{" "}
                    · Drops: {routeJob.quote.total_drops ?? "—"}
                  </p>
                  <div className="mt-3">
                    <QuoteLines
                      breakdown={routeJob.quote}
                      quotedCents={routeJob.quote.amount_cents}
                      chargedCents={routeJob.quote.amount_cents}
                      currency={(routeJob.quote.currency || "cad").toUpperCase()}
                    />
                  </div>
                </div>
              ) : (
                <p className="text-sm text-amber-700">
                  Quote unavailable until every stop geocodes successfully. Fix addresses below.
                </p>
              )}

              {routeJob.errors.length > 0 && (
                <div>
                  <h3 className="font-medium text-primary">Issues</h3>
                  <div className="mt-2">
                    <BulkErrorReport errors={routeJob.errors} />
                  </div>
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
                  <div className="flex flex-wrap items-end gap-2">
                    <Button variant="outline" onClick={onApplyMapping} disabled={loading}>
                      Apply mapping &amp; re-quote
                    </Button>
                    <label className="text-sm">
                      <span className="mb-1 block text-muted">Load saved mapping</span>
                      <select
                        className="rounded-xl border border-primary/15 px-3 py-2"
                        value={selectedProfileId}
                        onChange={(e) => setSelectedProfileId(e.target.value)}
                      >
                        <option value="">Select…</option>
                        {profiles.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <Button
                      variant="outline"
                      onClick={() => void onLoadMapping()}
                      disabled={loading || !selectedProfileId}
                    >
                      Load mapping
                    </Button>
                    <label className="text-sm">
                      <span className="mb-1 block text-muted">Save as</span>
                      <input
                        className="rounded-xl border border-primary/15 px-3 py-2"
                        value={mappingName}
                        onChange={(e) => setMappingName(e.target.value)}
                      />
                    </label>
                    <Button variant="ghost" onClick={() => void onSaveMapping()} disabled={loading}>
                      Save column mapping
                    </Button>
                  </div>
                  {routeJob.mapping_profile_name ? (
                    <p className="text-xs text-muted">
                      Using saved mapping: {routeJob.mapping_profile_name}
                    </p>
                  ) : null}
                </div>
              )}

              <div className="ops-table-scroll">
                <table className="min-w-[40rem] w-full text-left text-sm">
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
                    {routeJob.stops.map((stop, idx) => {
                      const geo = String(stop.geocode_status ?? "");
                      const needsFix = geo === "failed" || geo === "pending";
                      return (
                        <tr
                          key={idx}
                          className={
                            needsFix
                              ? "border-b border-amber-100 bg-amber-50/50"
                              : "border-b border-primary/5"
                          }
                        >
                          <td className="py-2 pr-3">{String(stop.sequence ?? idx + 1)}</td>
                          <td className="py-2 pr-3">{String(stop.stop_type ?? "")}</td>
                          <td className="py-2 pr-3 max-w-md truncate">
                            {String(stop.formatted || stop.raw_address || stop.address || "")}
                          </td>
                          <td className="py-2 pr-3">{String(stop.unit ?? "—")}</td>
                          <td className="py-2 pr-3">
                            {needsFix ? (
                              <span className="font-medium text-amber-800">{geo || "pending"}</span>
                            ) : (
                              geo
                            )}
                          </td>
                          <td className="py-2">
                            <button
                              type="button"
                              className="text-primary underline"
                              onClick={() => {
                                setEditingIndex(idx);
                                setEditPlace(null);
                                setEditAddress(
                                  String(stop.raw_address || stop.address || stop.formatted || "")
                                );
                              }}
                            >
                              {needsFix ? "Fix location" : "Edit"}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {editingIndex != null && (
                <div className="flex flex-wrap items-end gap-2 rounded-xl border border-primary/10 p-3">
                  <label className="min-w-[16rem] flex-1 text-sm">
                    <span className="mb-1 block font-medium">Stop {editingIndex + 1} address</span>
                    <AddressAutocompleteInput
                      id={`bulk-stop-fix-${editingIndex}`}
                      value={editAddress}
                      onChange={(value) => {
                        setEditAddress(value);
                        setEditPlace(null);
                      }}
                      onPlaceSelect={(place) => {
                        setEditAddress(place.formatted);
                        setEditPlace(place);
                      }}
                      placeholder="Start typing — pick a suggestion to lock the pin"
                      apiKey={publicEnv.googleMapsApiKey}
                      className="w-full"
                      fallbackClassName="w-full rounded-xl border border-primary/15 px-3 py-2"
                    />
                    <span className="mt-1 block text-xs text-muted">
                      {editPlace?.lat != null
                        ? "Location locked from Places (same as Book Delivery)."
                        : "Pick a suggestion to set the map pin. Typed-only addresses use OpenStreetMap."}
                    </span>
                  </label>
                  <Button onClick={onSaveStop} disabled={loading || !editAddress.trim()}>
                    {editPlace?.lat != null ? "Save location" : "Look up address"}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setEditingIndex(null);
                      setEditPlace(null);
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              )}

              {routeJob.route_geometry?.polyline && (
                <p className="text-xs text-muted">
                  Route ready ({routeJob.route_geometry.leg_count ?? "multi"} legs
                  {routeJob.optimized && routeJob.optimize_status !== "pending"
                    ? " · drop order updated"
                    : ""}
                  {optimizePending ? " · updating drop order…" : ""}).
                </p>
              )}

              <p className="rounded-xl border border-amber-200/80 bg-amber-50/70 px-3 py-2 text-xs text-amber-950">
                <span className="font-semibold">Drop-order reorder ≠ fleet Optimize.</span> This
                uses nearest-neighbor on your stops for quoting only. Driver stop order is decided
                later by Fleetbase VROOM — not this button.
              </p>

              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  onClick={onOptimize}
                  disabled={loading || optimizing || optimizePending || !quoteReady}
                >
                  {optimizing || optimizePending ? "Updating drop order…" : "Optimize drop order"}
                </Button>
                {!confirmed ? (
                  <Button
                    onClick={onRouteConfirm}
                    disabled={loading || optimizing || !canConfirmRoute}
                  >
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
                  {quotedPreviewRow ? (
                    <div className="mt-3 rounded-xl bg-gray-bg/60 px-4 py-3">
                      <p className="mb-2 text-xs text-muted">
                        Quote for row {String(quotedPreviewRow.row ?? 1)}
                      </p>
                      <QuoteLines
                        breakdown={quotedPreviewRow.pricing_breakdown as Record<string, unknown>}
                        quotedCents={Number(quotedPreviewRow.estimated_amount_cents) || null}
                        chargedCents={Number(quotedPreviewRow.estimated_amount_cents) || null}
                      />
                    </div>
                  ) : null}
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
