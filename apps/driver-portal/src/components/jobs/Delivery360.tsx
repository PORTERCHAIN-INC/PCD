"use client";

import Link from "next/link";
import { useState } from "react";
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  KeyRound,
  MapPin,
  Navigation,
  Package,
  PenLine,
  Truck,
} from "lucide-react";
import { driverApi } from "@/lib/api";
import { enqueueOfflineAction } from "@/lib/offline-client";
import type { DriverJobDetail, JobActionKey } from "@/lib/jobs";
import {
  actionErrorMessage,
  getJobLeg,
  getPrimaryAction,
  isInDeliveryPhase,
  isInPickupPhase,
  isJobCompleted,
  jobStatusLabel,
  JOB_STEPS,
  resolveScanProgress,
  stepIndexForState,
  vehicleLabel,
  STOP_EXCEPTION_TYPES,
  formatAccessLine,
} from "@/lib/jobs";
import { cn, formatCents } from "@/lib/utils";

function Section({
  title,
  icon: Icon,
  children,
  className,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-2xl bg-white p-5 shadow-sm", className)}>
      <h2 className="flex items-center gap-2 text-lg font-bold">
        <Icon className="h-5 w-5 text-[var(--secondary)]" />
        {title}
      </h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function DetailRow({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div className="flex justify-between gap-4 border-b border-[var(--gray-bg)] py-2 text-sm last:border-0">
      <dt className="text-[var(--muted)]">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  );
}

function ProgressStepper({ state }: { state: string }) {
  const activeIdx = stepIndexForState(state);
  return (
    <ol className="flex flex-wrap gap-2">
      {JOB_STEPS.map((step, i) => {
        const done = i < activeIdx;
        const active = i === activeIdx;
        return (
          <li
            key={step.key}
            className={cn(
              "flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
              done && "bg-emerald-100 text-emerald-800",
              active &&
                !done &&
                "bg-[var(--secondary)]/15 text-[var(--secondary)] ring-1 ring-[var(--secondary)]/30",
              !done && !active && "bg-[var(--gray-bg)] text-[var(--muted)]"
            )}
          >
            {done ? <CheckCircle2 className="h-3.5 w-3.5" /> : null}
            {step.label}
          </li>
        );
      })}
    </ol>
  );
}

export default function Delivery360({
  job,
  routeId,
  onUpdated,
}: {
  job: DriverJobDetail;
  routeId: string | null;
  onUpdated: () => void;
}) {
  const [pending, setPending] = useState<string | null>(null);
  const [otp, setOtp] = useState("");
  const [photoUrl, setPhotoUrl] = useState("");
  const [signature, setSignature] = useState("");
  const [incidentType, setIncidentType] = useState("customer_not_available");
  const [incidentNotes, setIncidentNotes] = useState("");
  const [exceptionPhoto, setExceptionPhoto] = useState("");
  const [message, setMessage] = useState("");
  const [messageError, setMessageError] = useState(false);

  const [scanInput, setScanInput] = useState("");
  const [missingFor, setMissingFor] = useState<string | null>(null);
  const [missingReason, setMissingReason] = useState("not_found");
  const [missingPhoto, setMissingPhoto] = useState("");
  const rid = routeId ?? `route-${new Date().toISOString().slice(0, 10)}`;
  const pickupPhase = isInPickupPhase(job);
  const deliveryPhase = isInDeliveryPhase(job);
  const completed = isJobCompleted(job);
  const primary = getPrimaryAction(job.state, job.allowed_actions ?? []);
  const scanPhase: "pickup" | "delivery" = deliveryPhase ? "delivery" : "pickup";
  const scanProgress = resolveScanProgress(job, scanPhase);
  const wholeVehicle = job.booking_mode === "vehicle";
  const scansComplete = wholeVehicle || scanProgress.complete;
  const exceptionMeta = STOP_EXCEPTION_TYPES.find((item) => item.id === incidentType);
  const accessLine = formatAccessLine({
    special_instructions: job.special_instructions,
    access_unit:
      typeof job.delivery_detail.unit === "string"
        ? job.delivery_detail.unit
        : typeof job.next_stop?.access_unit === "string"
          ? job.next_stop.access_unit
          : null,
    access_buzzer: job.next_stop?.access_buzzer ?? null,
    access_dock: job.next_stop?.access_dock ?? null,
    call_on_arrival: job.next_stop?.call_on_arrival ?? false,
    contact_phone_masked: job.next_stop?.contact_phone_masked ?? null,
  });
  const stopId = deliveryPhase ? job.delivery_stop_id : job.pickup_stop_id;

  async function run(action: string, fn: () => Promise<unknown>) {
    setPending(action);
    setMessage("");
    setMessageError(false);
    try {
      await fn();
      setMessage(`${action.replace(/_/g, " ")} recorded`);
      onUpdated();
    } catch (e) {
      const raw = e instanceof Error ? e.message : "action_failed";
      setMessage(actionErrorMessage(raw));
      setMessageError(true);
    } finally {
      setPending(null);
    }
  }

  async function runPrimary(action: JobActionKey) {
    const map: Record<JobActionKey, () => Promise<unknown>> = {
      arrive_pickup: () => driverApi.arriveStop(rid, job.pickup_stop_id),
      confirm_pickup: () => driverApi.deliverStop(rid, job.pickup_stop_id),
      arrive_delivery: () => driverApi.arriveStop(rid, job.delivery_stop_id),
      confirm_delivery: () => driverApi.deliverStop(rid, job.delivery_stop_id),
    };
    await run(action, map[action]);
  }

  async function runUpload(
    action: string,
    offlineType: string,
    payload: Record<string, unknown>,
    fn: () => Promise<unknown>
  ) {
    setPending(action);
    setMessage("");
    setMessageError(false);
    try {
      await fn();
      setMessage(`${action.replace(/_/g, " ")} recorded`);
      onUpdated();
    } catch {
      enqueueOfflineAction(offlineType, payload);
      setMessage("Saved offline — will sync when connected");
    } finally {
      setPending(null);
    }
  }

  const pickup = job.pickup_detail;
  const delivery = job.delivery_detail;
  const leg = getJobLeg(job.state);

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-[var(--primary)] p-5 text-white shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-white/70">
              Delivery 360
            </p>
            <h1 className="text-2xl font-bold">{job.order_number}</h1>
            <p className="text-sm text-white/80">{job.tracking_number}</p>
            {job.shopify_order_label ? (
              <p className="mt-1 text-sm text-white/90">{job.shopify_order_label}</p>
            ) : null}
          </div>
          <span className="rounded-full bg-white/15 px-3 py-1 text-sm font-semibold">
            {jobStatusLabel(job.state)}
          </span>
        </div>
        <div className="mt-4">
          <ProgressStepper state={job.state} />
        </div>
        <p className="mt-3 text-sm text-white/90">
          {leg === "completed"
            ? "Job complete"
            : `${leg === "pickup" ? "Pickup" : "Delivery"} phase`}{" "}
          · Updated {job.updated_at ? new Date(job.updated_at).toLocaleTimeString() : "—"}
        </p>
        {!completed && (
          <Link
            href={`/navigation?order=${job.order_id}`}
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-white/15 px-4 py-2 text-sm font-semibold hover:bg-white/25"
          >
            <Navigation className="h-4 w-4" />
            Open Navigation
          </Link>
        )}
      </div>

      {!job.is_current_job && job.next_stop && !completed && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          This is not your next stop.{" "}
          <Link href={`/jobs/${job.next_stop.order_id}`} className="font-semibold underline">
            Go to {job.next_stop.order_number ?? "current job"}
          </Link>
        </div>
      )}

      {message && (
        <p
          className={cn(
            "rounded-xl px-4 py-2 text-sm font-medium",
            messageError ? "bg-red-50 text-red-800" : "bg-emerald-50 text-emerald-800"
          )}
        >
          {message}
        </p>
      )}

      {!completed && primary && (
        <div className="rounded-2xl border border-[var(--secondary)]/25 bg-gradient-to-br from-[var(--secondary)]/8 to-transparent p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--secondary)]">
            Next action
          </p>
          <p className="mt-1 text-lg font-bold">
            {primary.key.includes("pickup") ? job.pickup_address : job.delivery_address}
          </p>
          {accessLine ? <p className="mt-2 text-sm text-amber-900">{accessLine}</p> : null}
          {(job.delivery_attempts ?? 0) > 0 ? (
            <p className="mt-1 text-xs font-semibold text-[var(--muted)]">
              Attempt {job.delivery_attempts} of {job.max_delivery_attempts ?? 2}
            </p>
          ) : null}
          {primary.key.startsWith("confirm_") && !scansComplete ? (
            <p className="mt-2 text-sm text-amber-800">
              Scan or report every package first ({scanProgress.scanned}/{scanProgress.required})
            </p>
          ) : null}
          {wholeVehicle ? (
            <p className="mt-2 text-sm text-[var(--muted)]">
              Whole vehicle · {vehicleLabel(job.vehicle_class)}. No parcel labels.
            </p>
          ) : null}
          <button
            type="button"
            disabled={
              pending === primary.key || (primary.key.startsWith("confirm_") && !scansComplete)
            }
            onClick={() => runPrimary(primary.key)}
            className={cn(
              "mt-4 w-full rounded-xl py-3.5 text-sm font-bold text-white disabled:opacity-50",
              primary.key.includes("delivery")
                ? "bg-emerald-600 hover:bg-emerald-700"
                : "bg-[var(--primary)]"
            )}
          >
            {pending === primary.key ? "Working…" : primary.label}
          </button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Section
          title="Pickup"
          icon={Package}
          className={cn(job.pickup_completed && "border border-emerald-200/60")}
        >
          {job.pickup_completed ? (
            <div className="mb-4 flex items-center gap-2 rounded-xl bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-800">
              <CheckCircle2 className="h-5 w-5" />
              Parcel picked up
              {job.pickup_completed_at && (
                <span className="ml-auto text-xs font-normal text-emerald-700">
                  {new Date(job.pickup_completed_at).toLocaleString()}
                </span>
              )}
            </div>
          ) : null}
          <dl>
            <DetailRow label="Address" value={job.pickup_address} />
            <DetailRow label="Contact" value={String(pickup.name ?? pickup.contact_name ?? "")} />
            <DetailRow label="Phone" value={String(pickup.phone ?? "")} />
            <DetailRow label="Status" value={String(job.pickup_stop.status ?? "")} />
          </dl>
          {pickupPhase && !job.pickup_completed && primary?.key === "arrive_pickup" && (
            <p className="mt-3 text-xs text-[var(--muted)]">
              Tap the primary action above when you reach the pickup location.
            </p>
          )}
        </Section>

        {deliveryPhase ? (
          <Section title="Delivery" icon={Truck}>
            <dl>
              <DetailRow label="Address" value={job.delivery_address} />
              <DetailRow label="Customer" value={job.customer.name} />
              <DetailRow label="Phone" value={job.customer.phone} />
              <DetailRow label="Email" value={job.customer.email} />
              <DetailRow label="Status" value={String(job.delivery_stop.status ?? "")} />
            </dl>
            {deliveryPhase && !completed && primary?.key.startsWith("arrive_delivery") && (
              <p className="mt-3 text-xs text-[var(--muted)]">
                Navigate to the customer, then confirm arrival and delivery.
              </p>
            )}
          </Section>
        ) : (
          <div className="flex items-center justify-center rounded-2xl border border-dashed border-[var(--primary)]/15 bg-white/60 p-8 text-center">
            <div>
              <Truck className="mx-auto h-8 w-8 text-[var(--muted)]" />
              <p className="mt-2 text-sm font-medium text-[var(--muted)]">
                Delivery unlocks after pickup
              </p>
            </div>
          </div>
        )}
      </div>

      {completed && (
        <Section title="Completed" icon={CheckCircle2}>
          <p className="text-sm text-[var(--muted)]">
            This delivery is complete. Review timeline and proof below.
          </p>
          {job.delivery_completed_at && (
            <p className="mt-2 text-sm font-semibold text-emerald-700">
              Delivered {new Date(job.delivery_completed_at).toLocaleString()}
            </p>
          )}
        </Section>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {job.merchant && (
          <Section title="Merchant" icon={Package}>
            <dl>
              <DetailRow label="Company" value={job.merchant.company_name} />
              <DetailRow label="Email" value={job.merchant.email} />
              <DetailRow label="Phone" value={job.merchant.phone} />
            </dl>
          </Section>
        )}

        <Section title="Customer" icon={MapPin}>
          <dl>
            <DetailRow label="Name" value={job.customer.name} />
            <DetailRow label="Phone" value={job.customer.phone} />
            <DetailRow label="Email" value={job.customer.email} />
            <DetailRow label="Order value" value={formatCents(job.amount_cents)} />
            {job.declared_value_cents ? (
              <DetailRow label="Declared value" value={formatCents(job.declared_value_cents)} />
            ) : null}
            {job.vehicle_class || wholeVehicle ? (
              <DetailRow
                label="Vehicle"
                value={
                  wholeVehicle
                    ? `Whole vehicle · ${vehicleLabel(job.vehicle_class)}`
                    : vehicleLabel(job.vehicle_class)
                }
              />
            ) : null}
          </dl>
        </Section>
      </div>

      <Section title={wholeVehicle ? "Load" : "Packages"} icon={Package}>
        {wholeVehicle ? (
          <p className="text-sm text-[var(--muted)]">
            Whole vehicle · {vehicleLabel(job.vehicle_class)}. Nothing to scan.
          </p>
        ) : (
          <p className="mb-3 text-sm font-semibold text-[var(--primary)]">
            Scanned {scanProgress.scanned}/{scanProgress.required}
            {scanProgress.complete ? " · ready" : " · scan all boxes before confirm"}
          </p>
        )}
        {wholeVehicle ? null : job.packages_error ? (
          <p className="text-sm text-red-600">Package list unavailable — refresh and try again.</p>
        ) : job.packages.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No package details on file</p>
        ) : (
          <ul className="space-y-3">
            {job.packages.map((pkg, i) => {
              const done =
                scanPhase === "delivery"
                  ? Boolean(pkg.scanned_delivery)
                  : Boolean(pkg.scanned_pickup);
              return (
                <li
                  key={String(pkg.id ?? pkg.tracking_suffix ?? i)}
                  className="rounded-xl bg-[var(--gray-bg)] p-3 text-sm"
                >
                  <p className="font-semibold">
                    {pkg.preset_label ||
                      (pkg.tracking_suffix
                        ? `BOX ${pkg.parcel_index ?? i + 1} of ${pkg.total_parcels ?? job.packages.length}`
                        : String(pkg.package_type ?? "Package"))}
                    {pkg.item_key && (pkg.box_count ?? 0) > 1
                      ? ` · item box ${pkg.box_index ?? "?"} of ${pkg.box_count}`
                      : ""}
                    {pkg.instructions ? ` · ${pkg.instructions}` : ""}
                    {done ? " · scanned" : ""}
                    {pkg.missing_at_pickup ? " · reported missing" : ""}
                  </p>
                  <p className="text-[var(--muted)]">
                    {pkg.tracking_suffix ?? "—"}
                    {pkg.weight_kg != null ? ` · ${pkg.weight_kg} kg` : ""}
                    {pkg.status ? ` · ${pkg.status}` : ""}
                  </p>
                  {scanPhase === "pickup" &&
                  !completed &&
                  !done &&
                  !pkg.missing_at_pickup &&
                  pkg.id ? (
                    missingFor === pkg.id ? (
                      <div className="mt-2 space-y-2">
                        <select
                          value={missingReason}
                          onChange={(e) => setMissingReason(e.target.value)}
                          className="w-full rounded-xl border px-3 py-2 text-sm"
                        >
                          <option value="not_ready">Not ready</option>
                          <option value="not_found">Not found</option>
                          <option value="damaged">Damaged</option>
                          <option value="wrong_item">Wrong item</option>
                          <option value="other">Other</option>
                        </select>
                        <input
                          value={missingPhoto}
                          onChange={(e) => setMissingPhoto(e.target.value)}
                          placeholder="Photo URL (required)"
                          className="w-full rounded-xl border px-3 py-2 text-sm"
                        />
                        <button
                          type="button"
                          disabled={pending === "report_missing" || !missingPhoto.trim()}
                          onClick={() =>
                            run("report_missing", async () => {
                              await driverApi.reportPackageMissing(job.order_id, String(pkg.id), {
                                photo_url: missingPhoto.trim(),
                                reason: missingReason,
                              });
                              setMissingFor(null);
                              setMissingPhoto("");
                            })
                          }
                          className="rounded-xl bg-red-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-50"
                        >
                          {pending === "report_missing" ? "…" : "Report box missing"}
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          setMissingFor(String(pkg.id));
                          setMissingPhoto("");
                        }}
                        className="mt-2 text-xs font-semibold text-red-600 underline"
                      >
                        Not here? Report missing
                      </button>
                    )
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
        {!completed ? (
          <div className="mt-3 space-y-2">
            <label className="text-xs font-semibold text-[var(--muted)]">
              Scan PorterChain label ({scanPhase})
            </label>
            <div className="flex gap-2">
              <input
                value={scanInput}
                onChange={(e) => setScanInput(e.target.value)}
                placeholder="QR payload or tracking line"
                className="flex-1 rounded-xl border px-3 py-2 text-sm"
              />
              <button
                type="button"
                disabled={pending === "scan" || !scanInput.trim()}
                onClick={() =>
                  run("scan", async () => {
                    await driverApi.scanPackage(job.order_id, {
                      qr_payload: scanInput.trim(),
                      phase: scanPhase,
                    });
                    setScanInput("");
                  })
                }
                className="rounded-xl bg-[var(--secondary)] px-3 text-xs font-bold text-white disabled:opacity-50"
              >
                {pending === "scan" ? "…" : "Scan"}
              </button>
            </div>
          </div>
        ) : null}
      </Section>

      {job.special_instructions && (
        <Section title="Special Instructions" icon={AlertTriangle}>
          <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-900">
            {job.special_instructions}
          </p>
        </Section>
      )}

      {deliveryPhase && !completed && (
        <Section title="Proof of Delivery" icon={CheckCircle2}>
          <div className="grid gap-4 sm:grid-cols-2">
            {job.otp_required ? (
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-semibold">
                  <KeyRound className="h-4 w-4" /> OTP
                </label>
                <p className="text-xs text-[var(--muted)]">
                  Merchant asked for receiver verification. Enter the code they give you.
                </p>
                <div className="flex gap-2">
                  <input
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    placeholder="6-digit OTP"
                    className="flex-1 rounded-xl border px-3 py-2 text-sm"
                  />
                  <button
                    type="button"
                    disabled={pending === "otp_gen"}
                    onClick={() => run("otp_gen", () => driverApi.generateOtp(job.order_id))}
                    className="rounded-xl bg-[var(--gray-bg)] px-3 text-xs font-semibold"
                  >
                    Generate
                  </button>
                </div>
              </div>
            ) : null}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-semibold">
                <Camera className="h-4 w-4" /> Photo URL
              </label>
              <input
                value={photoUrl}
                onChange={(e) => setPhotoUrl(e.target.value)}
                placeholder="https://..."
                className="w-full rounded-xl border px-3 py-2 text-sm"
              />
              <button
                type="button"
                disabled={!photoUrl || pending === "photo"}
                onClick={() =>
                  runUpload(
                    "photo",
                    "camera_upload",
                    { stop_id: job.delivery_stop_id, file_url: photoUrl, route_id: rid },
                    () => driverApi.podPhoto(rid, job.delivery_stop_id, photoUrl)
                  )
                }
                className="text-xs font-semibold text-[var(--secondary)]"
              >
                Upload photo
              </button>
            </div>
            <div className="space-y-2 sm:col-span-2">
              <label className="flex items-center gap-2 text-sm font-semibold">
                <PenLine className="h-4 w-4" /> Signature
              </label>
              <textarea
                value={signature}
                onChange={(e) => setSignature(e.target.value)}
                rows={2}
                className="w-full rounded-xl border px-3 py-2 text-sm"
              />
              <button
                type="button"
                disabled={!signature || pending === "signature"}
                onClick={() =>
                  runUpload(
                    "signature",
                    "pod_signature",
                    { stop_id: job.delivery_stop_id, signature_data: signature, route_id: rid },
                    () => driverApi.podSignature(rid, job.delivery_stop_id, signature)
                  )
                }
                className="text-xs font-semibold text-[var(--secondary)]"
              >
                Save signature
              </button>
            </div>
          </div>
          {(job.cod_amount_cents ?? 0) > 0 && (
            <div className="mt-4 rounded-xl border border-[var(--border)] bg-[var(--gray-bg)] p-3">
              <p className="text-sm font-semibold text-[var(--primary)]">
                COD · {((job.cod_amount_cents ?? 0) / 100).toFixed(2)}{" "}
                {(job.currency || "cad").toUpperCase()}
              </p>
              <p className="mt-1 text-xs text-[var(--muted)]">
                Status: {job.cod_status || "pending"} — scan all boxes before Payment Link
              </p>
              {!job.scan_pickup?.complete ? (
                <p className="mt-2 text-xs text-amber-800">
                  Pickup scans {job.scan_pickup?.scanned ?? 0}/{job.scan_pickup?.required ?? 0}{" "}
                  required
                </p>
              ) : null}
              <button
                type="button"
                disabled={
                  pending === "cod_checkout" ||
                  job.cod_status === "collected" ||
                  job.cod_status === "payout_processed" ||
                  !job.scan_pickup?.complete
                }
                onClick={() =>
                  run("cod_checkout", async () => {
                    const res = await driverApi.codCheckout(job.order_id);
                    if (res.checkout_url) {
                      window.open(res.checkout_url, "_blank", "noopener,noreferrer");
                    }
                    return res;
                  })
                }
                className="mt-3 w-full rounded-xl border border-[var(--secondary)] py-2 text-sm font-bold text-[var(--secondary)] disabled:opacity-50"
              >
                {pending === "cod_checkout" ? "Opening…" : "Collect COD (Payment Link)"}
              </button>
            </div>
          )}
          <button
            type="button"
            disabled={pending === "pod_complete" || (Boolean(job.otp_required) && !otp.trim())}
            onClick={() =>
              run("pod_complete", () =>
                driverApi.podComplete(rid, job.delivery_stop_id, otp.trim() || undefined)
              )
            }
            className="mt-4 w-full rounded-xl bg-[var(--secondary)] py-3 text-sm font-bold text-white disabled:opacity-50"
          >
            {pending === "pod_complete" ? "Completing…" : "Complete POD"}
          </button>
          <p className="mt-2 text-xs text-[var(--muted)]">
            POD status: {job.proof_of_delivery.completed ? "Completed" : "Pending"}
            {job.otp_required && job.proof_of_delivery.otp_verified ? " · OTP set" : ""}
          </p>
        </Section>
      )}

      <Section title="Photos & Documents" icon={Camera}>
        {job.photos.length === 0 && job.documents.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No captures yet</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {[...job.photos, ...job.documents, ...job.signatures].map((p, i) => (
              <li key={i} className="rounded-lg bg-[var(--gray-bg)] px-3 py-2">
                <span className="font-semibold capitalize">{String(p.type)}</span>
                <span className="text-[var(--muted)]"> — {String(p.value ?? "").slice(0, 80)}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Timeline" icon={Navigation}>
        {job.timeline.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No events yet</p>
        ) : (
          <ol className="relative space-y-4 border-l-2 border-[var(--secondary)]/30 pl-4">
            {job.timeline.map((ev, i) => (
              <li key={i} className="text-sm">
                <p className="font-semibold">{ev.label}</p>
                <p className="text-xs text-[var(--muted)]">
                  {ev.occurred_at ? new Date(ev.occurred_at).toLocaleString() : "—"}
                  {ev.to_state ? ` → ${ev.to_state}` : ""}
                </p>
              </li>
            ))}
          </ol>
        )}
      </Section>

      {!completed && (
        <Section title="Cannot complete this stop" icon={AlertTriangle}>
          <div className="space-y-3">
            <select
              value={incidentType}
              onChange={(e) => setIncidentType(e.target.value)}
              className="w-full rounded-xl border px-3 py-2 text-sm"
            >
              {STOP_EXCEPTION_TYPES.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
            {exceptionMeta?.photoRequired ? (
              <input
                value={exceptionPhoto}
                onChange={(e) => setExceptionPhoto(e.target.value)}
                placeholder="Photo URL required for this reason"
                className="w-full rounded-xl border px-3 py-2 text-sm"
              />
            ) : (
              <input
                value={exceptionPhoto}
                onChange={(e) => setExceptionPhoto(e.target.value)}
                placeholder="Photo URL (optional)"
                className="w-full rounded-xl border px-3 py-2 text-sm"
              />
            )}
            <textarea
              value={incidentNotes}
              onChange={(e) => setIncidentNotes(e.target.value)}
              placeholder="Notes for ops / claims…"
              rows={3}
              className="w-full rounded-xl border px-3 py-2 text-sm"
            />
            <button
              type="button"
              disabled={
                pending === "exception" ||
                (Boolean(exceptionMeta?.photoRequired) && !exceptionPhoto.trim())
              }
              onClick={() =>
                run("exception", () =>
                  driverApi.reportException(rid, stopId, {
                    exception_type: incidentType,
                    notes: incidentNotes.trim() || exceptionMeta?.label,
                    photo_url: exceptionPhoto.trim() || undefined,
                  })
                )
              }
              className={cn(
                "w-full rounded-xl py-2.5 text-sm font-semibold text-white",
                "bg-red-600 hover:bg-red-700 disabled:opacity-50"
              )}
            >
              {pending === "exception"
                ? "Submitting…"
                : exceptionMeta?.retryable
                  ? "Log attempt — stay on stop"
                  : "Fail this stop"}
            </button>
          </div>
          {job.incidents.length > 0 && (
            <ul className="mt-4 space-y-2">
              {job.incidents.map((inc) => (
                <li key={inc.id} className="rounded-lg bg-[var(--gray-bg)] px-3 py-2 text-sm">
                  <span className="font-semibold capitalize">{inc.incident_type}</span> —{" "}
                  {inc.status}
                  <p className="text-xs text-[var(--muted)]">{inc.description}</p>
                </li>
              ))}
            </ul>
          )}
        </Section>
      )}
    </div>
  );
}
