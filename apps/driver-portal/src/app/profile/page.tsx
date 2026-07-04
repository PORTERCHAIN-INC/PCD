"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  Bell,
  Car,
  FileText,
  RefreshCw,
  Shield,
  Upload,
  User,
  Wrench,
} from "lucide-react";
import DriverShell from "@/components/DriverShell";
import { useDriverProfile } from "@/hooks/useDriverProfile";
import { hasDriverSession } from "@/lib/api";
import {
  formatProfileDate,
  severityStyles,
  statusBadge,
  UPLOADABLE_DOC_TYPES,
} from "@/lib/profile";
import { cn } from "@/lib/utils";

export default function ProfilePage() {
  const router = useRouter();
  const {
    data,
    error,
    loading,
    refreshing,
    uploading,
    refresh,
    uploadDocument,
    uploadVehiclePhoto,
  } = useDriverProfile();

  useEffect(() => {
    hasDriverSession().then((ok) => {
      if (!ok) router.replace("/login");
    });
  }, [router]);

  if (loading && !data) {
    return (
      <DriverShell>
        <div className="animate-pulse space-y-4">
          <div className="h-10 w-48 rounded-xl bg-white" />
          <div className="h-40 rounded-2xl bg-white" />
        </div>
      </DriverShell>
    );
  }

  const snap = data!;

  return (
    <DriverShell>
      <header className="flex flex-col gap-3 border-b border-[var(--primary)]/8 pb-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Profile & Compliance</h1>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Documents, vehicle, and verification — managed in Porterchain
          </p>
        </div>
        <button
          type="button"
          onClick={refresh}
          disabled={refreshing}
          className="inline-flex items-center gap-2 rounded-xl border border-[var(--primary)]/10 bg-white px-4 py-2 text-sm font-medium"
        >
          <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
          {refreshing ? "Syncing…" : "Sync now"}
        </button>
      </header>

      {error && (
        <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      )}

      {snap.expiry_notifications.length > 0 && (
        <section className="mt-6 space-y-2">
          {snap.expiry_notifications.map((n) => (
            <div
              key={`${n.category}-${n.expires_at}`}
              className={cn(
                "flex items-start gap-3 rounded-xl px-4 py-3 text-sm",
                severityStyles(n.severity)
              )}
            >
              <Bell className="mt-0.5 h-4 w-4 shrink-0" />
              <p>{n.message}</p>
            </div>
          ))}
        </section>
      )}

      <section className="mt-6 rounded-2xl bg-white p-5 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[var(--secondary)]/10">
            <User className="h-7 w-7 text-[var(--secondary)]" />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-xl font-bold">{snap.profile.full_name}</h2>
            <p className="text-sm text-[var(--muted)]">{snap.profile.email}</p>
            {snap.profile.phone && (
              <p className="text-sm text-[var(--muted)]">{snap.profile.phone}</p>
            )}
            <div className="mt-2 flex flex-wrap gap-2">
              <Badge label={snap.profile.status} />
              {snap.profile.rating != null && (
                <span className="rounded-full bg-[var(--gray-bg)] px-2 py-0.5 text-xs font-semibold">
                  ★ {snap.profile.rating.toFixed(1)}
                </span>
              )}
            </div>
            <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
              <Row label="Service area" value={snap.profile.service_area} />
              <Row label="Location" value={[snap.profile.city, snap.profile.province].filter(Boolean).join(", ") || null} />
              <Row label="License class" value={snap.profile.license_class} />
            </dl>
          </div>
        </div>
      </section>

      <section id="insurance" className="mt-6 grid gap-4 lg:grid-cols-2">
        <ComplianceCard title="License" icon={FileText} verified={snap.license.verified}>
          <Row label="Status" value={snap.license.status} />
          <Row label="Number" value={snap.license.number} />
          <Row label="Expires" value={formatProfileDate(snap.license.expires_at)} />
        </ComplianceCard>
        <ComplianceCard title="Insurance" icon={Shield} verified={snap.verification.insurance_verified}>
          <Row label="Provider" value={String(snap.insurance.provider ?? "—")} />
          <Row label="Policy" value={String(snap.insurance.policy_number ?? "—")} />
          <Row label="Expires" value={formatProfileDate(String(snap.insurance.expires_at ?? ""))} />
        </ComplianceCard>
        <ComplianceCard title="Registration" icon={Car} verified={snap.registration.verified}>
          <Row label="Plate" value={snap.registration.plate_number ?? snap.vehicle?.plate_number} />
          <Row label="Status" value={snap.registration.status} />
          <Row label="Expires" value={formatProfileDate(snap.registration.expires_at)} />
        </ComplianceCard>
        <ComplianceCard
          title="Background Check"
          icon={AlertTriangle}
          verified={snap.background_check.passed}
        >
          <Row label="Status" value={snap.background_check.status} />
          <Row label="Completed" value={formatProfileDate(snap.background_check.completed_at)} />
          <Row label="Expires" value={formatProfileDate(snap.background_check.expires_at)} />
        </ComplianceCard>
      </section>

      <section id="vehicle" className="mt-6 rounded-2xl bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <Car className="h-5 w-5 text-[var(--secondary)]" />
          <h2 className="text-lg font-bold">Vehicle</h2>
        </div>
        {snap.vehicle ? (
          <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
            <Row label="Unit" value={snap.vehicle.make_model} />
            <Row label="Plate" value={snap.vehicle.plate_number} />
            <Row label="Class" value={snap.vehicle.vehicle_class} />
            <Row label="Capacity" value={snap.vehicle.capacity_kg ? `${snap.vehicle.capacity_kg} kg` : null} />
            <Row label="Compliance expires" value={formatProfileDate(snap.vehicle.compliance_expires_at)} />
          </dl>
        ) : (
          <p className="mt-4 text-sm text-[var(--muted)]">No active vehicle on file</p>
        )}
      </section>

      <section className="mt-6 grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <Wrench className="h-5 w-5 text-[var(--secondary)]" />
            <h2 className="text-lg font-bold">Maintenance Status</h2>
          </div>
          <dl className="mt-4 space-y-2 text-sm">
            <Row label="Status" value={snap.maintenance_status.status} />
            <Row label="Last service" value={formatProfileDate(snap.maintenance_status.last_service_at)} />
            <Row label="Next due" value={formatProfileDate(snap.maintenance_status.next_service_due)} />
            {snap.maintenance_status.notes && (
              <Row label="Notes" value={snap.maintenance_status.notes} />
            )}
          </dl>
        </div>
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold">Expiry Dates</h2>
          <ul className="mt-4 space-y-2">
            {snap.expiry_dates.length === 0 ? (
              <li className="text-sm text-[var(--muted)]">No expiry dates on file</li>
            ) : (
              snap.expiry_dates.map((e) => (
                <li
                  key={`${e.category}-${e.expires_at}`}
                  className="flex items-center justify-between gap-3 rounded-xl bg-[var(--gray-bg)] px-3 py-2 text-sm"
                >
                  <span>{e.label}</span>
                  <span className={cn("rounded-full px-2 py-0.5 text-xs font-semibold", severityStyles(e.severity))}>
                    {formatProfileDate(e.expires_at)}
                  </span>
                </li>
              ))
            )}
          </ul>
        </div>
      </section>

      <section className="mt-6 rounded-2xl bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold">Vehicle Photos</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {snap.vehicle_photos.length === 0 && (
            <p className="text-sm text-[var(--muted)] sm:col-span-2">No photos uploaded</p>
          )}
          {snap.vehicle_photos.map((p) => (
            <div key={p.id} className="rounded-xl border border-[var(--primary)]/10 p-3">
              {p.url ? (
                <a href={p.url} target="_blank" rel="noopener noreferrer" className="block truncate text-sm text-[var(--secondary)] underline">
                  {p.label || "View photo"}
                </a>
              ) : (
                <p className="text-sm">{p.label}</p>
              )}
              <p className="mt-1 text-xs capitalize text-[var(--muted)]">{p.status}</p>
            </div>
          ))}
        </div>
        <UploadVehiclePhotoForm
          uploading={uploading === "vehicle_photo"}
          onUpload={uploadVehiclePhoto}
        />
      </section>

      <section id="documents" className="mt-6 rounded-2xl bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold">Documents</h2>
        <ul className="mt-4 space-y-3">
          {snap.documents.map((doc) => (
            <li key={doc.type} className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-[var(--gray-bg)] px-4 py-3">
              <div>
                <p className="font-medium">{doc.label}</p>
                <p className="text-xs text-[var(--muted)]">
                  Expires {formatProfileDate(doc.expires_at)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn("rounded-full px-2 py-0.5 text-xs font-semibold capitalize", statusBadge(doc.status))}>
                  {doc.status.replace(/_/g, " ")}
                </span>
                {doc.url && (
                  <a href={doc.url} target="_blank" rel="noopener noreferrer" className="text-xs font-semibold text-[var(--secondary)]">
                    View
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
        <DocumentUploadForm uploading={uploading} onUpload={uploadDocument} />
      </section>

      <section className="mt-6 rounded-2xl border border-[var(--primary)]/10 bg-[var(--gray-bg)] p-5">
        <h2 className="text-lg font-bold">Contract (read-only)</h2>
        {snap.contract.has_contract ? (
          <dl className="mt-4 space-y-2 text-sm">
            <Row label="Agreement" value={snap.contract.contract_name} />
            <Row label="Type" value={snap.contract.contract_type} />
            <Row label="Pay model" value={snap.contract.pay_model} />
            <Row label="Effective from" value={formatProfileDate(snap.contract.effective_from)} />
            <Row label="Effective to" value={formatProfileDate(snap.contract.effective_to)} />
            {snap.contract.terms_url && (
              <div className="pt-2">
                <a
                  href={snap.contract.terms_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-semibold text-[var(--secondary)] underline"
                >
                  View contract terms
                </a>
              </div>
            )}
            {snap.contract.notes && <p className="mt-2 text-xs text-[var(--muted)]">{snap.contract.notes}</p>}
          </dl>
        ) : (
          <p className="mt-3 text-sm text-[var(--muted)]">{snap.contract.message}</p>
        )}
        <p className="mt-4 text-xs text-[var(--muted)]">
          Contract terms are managed by Porterchain operations. Contact support to request changes.
        </p>
      </section>

      <p className="mt-6 text-xs text-[var(--muted)]">
        Last synced {new Date(snap.last_updated).toLocaleString()}
      </p>
    </DriverShell>
  );
}

function ComplianceCard({
  title,
  icon: Icon,
  verified,
  children,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  verified: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon className="h-5 w-5 text-[var(--secondary)]" />
          <h2 className="text-lg font-bold">{title}</h2>
        </div>
        <span className={cn("rounded-full px-2 py-0.5 text-xs font-semibold", verified ? statusBadge("verified") : statusBadge("pending"))}>
          {verified ? "Verified" : "Pending"}
        </span>
      </div>
      <dl className="mt-4 space-y-2 text-sm">{children}</dl>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-[var(--muted)]">{label}</dt>
      <dd className="text-right font-semibold capitalize">{value || "—"}</dd>
    </div>
  );
}

function Badge({ label }: { label: string }) {
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-xs font-semibold capitalize", statusBadge(label))}>
      {label.replace(/_/g, " ")}
    </span>
  );
}

function DocumentUploadForm({
  uploading,
  onUpload,
}: {
  uploading: string | null;
  onUpload: (type: string, url: string, meta?: Record<string, string>) => Promise<void>;
}) {
  const [docType, setDocType] = useState("license");
  const [fileUrl, setFileUrl] = useState("");
  const [expiresAt, setExpiresAt] = useState("");

  return (
    <form
      className="mt-6 space-y-3 border-t border-[var(--primary)]/10 pt-4"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!fileUrl.trim()) return;
        await onUpload(docType, fileUrl.trim(), expiresAt ? { expires_at: expiresAt } : undefined);
        setFileUrl("");
        setExpiresAt("");
      }}
    >
      <p className="text-sm font-semibold">Upload document</p>
      <select
        value={docType}
        onChange={(e) => setDocType(e.target.value)}
        className="w-full rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
      >
        {UPLOADABLE_DOC_TYPES.map((t) => (
          <option key={t.value} value={t.value}>
            {t.label}
          </option>
        ))}
      </select>
      <input
        type="url"
        required
        placeholder="Document file URL"
        value={fileUrl}
        onChange={(e) => setFileUrl(e.target.value)}
        className="w-full rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
      />
      <input
        type="date"
        value={expiresAt}
        onChange={(e) => setExpiresAt(e.target.value)}
        className="w-full rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
      />
      <button
        type="submit"
        disabled={Boolean(uploading)}
        className="inline-flex items-center gap-2 rounded-xl bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
      >
        <Upload className="h-4 w-4" />
        {uploading ? "Uploading…" : "Submit for review"}
      </button>
    </form>
  );
}

function UploadVehiclePhotoForm({
  uploading,
  onUpload,
}: {
  uploading: boolean;
  onUpload: (url: string, label?: string) => Promise<void>;
}) {
  const [fileUrl, setFileUrl] = useState("");
  const [label, setLabel] = useState("");

  return (
    <form
      className="mt-4 space-y-3 border-t border-[var(--primary)]/10 pt-4"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!fileUrl.trim()) return;
        await onUpload(fileUrl.trim(), label.trim() || undefined);
        setFileUrl("");
        setLabel("");
      }}
    >
      <p className="text-sm font-semibold">Upload vehicle photo</p>
      <input
        type="url"
        required
        placeholder="Photo URL"
        value={fileUrl}
        onChange={(e) => setFileUrl(e.target.value)}
        className="w-full rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
      />
      <input
        type="text"
        placeholder="Label (optional)"
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        className="w-full rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
      />
      <button
        type="submit"
        disabled={uploading}
        className="inline-flex items-center gap-2 rounded-xl bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
      >
        <Upload className="h-4 w-4" />
        {uploading ? "Uploading…" : "Upload photo"}
      </button>
    </form>
  );
}
