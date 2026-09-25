"use client";

import { useState } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { drivers, type DriverDetail } from "@/lib/drivers";
import { AddDriverDocumentForm } from "@/components/drivers/AddDriverDocumentForm";
import { Badge, Button, SectionCard, Spinner } from "@/components/crm/primitives";
import { shortDate, titleCase } from "@/lib/crmFormat";

export function DocumentsTab({
  id,
  driver,
  canWrite,
  onChanged,
}: {
  id: string;
  driver: DriverDetail;
  canWrite: boolean;
  onChanged: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [docVersion, setDocVersion] = useState(0);
  const [reasonFor, setReasonFor] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [docError, setDocError] = useState<string | null>(null);
  const { data, error } = useApiData((t) => drivers.documents(t, id), [id, docVersion], {
    key: `driver-documents-${id}`,
  });
  if (!data && !error) return <Spinner />;
  const v = data?.verification ?? {
    license_verified: driver.license_verified,
    insurance_verified: driver.insurance_verified,
    vehicle_verified: driver.vehicle_verified,
    background_check_status: driver.background_check_status,
  };
  const files = data?.files ?? [];
  const expiries = data?.expiries ?? [];
  const refreshDocs = () => {
    setDocVersion((n) => n + 1);
    onChanged();
  };
  async function decide(docType: string, decision: "verified" | "rejected", why?: string) {
    setDocError(null);
    try {
      const token = await getApiToken();
      await drivers.decideDocument(token, id, { doc_type: docType, decision, reason: why });
      setReasonFor(null);
      setReason("");
      refreshDocs();
    } catch (err) {
      setDocError(err instanceof Error ? err.message : "Could not update document");
    }
  }
  const attestTypes = [
    { type: "license", label: "License" },
    { type: "insurance", label: "Insurance" },
    { type: "vehicle_registration", label: "Vehicle" },
    { type: "background_check", label: "Background check" },
  ];
  return (
    <div className="space-y-5">
      {error && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          Could not load document metadata: {error}. Showing verification from driver profile.
        </p>
      )}
      {docError && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {docError}
        </p>
      )}
      {canWrite && (
        <SectionCard title="Verify without a file">
          <div className="flex flex-wrap gap-2 p-5">
            {attestTypes.map((item) => (
              <Button
                key={item.type}
                variant="outline"
                onClick={() => void decide(item.type, "verified")}
              >
                Verify {item.label}
              </Button>
            ))}
          </div>
        </SectionCard>
      )}
      <div className="grid gap-5 md:grid-cols-2">
        <SectionCard title="Verification">
          <div className="space-y-2 p-5">
            <VerifyRow
              label="Driver license"
              ok={v.license_verified}
              source={data?.sources?.license}
            />
            <VerifyRow
              label="Insurance"
              ok={v.insurance_verified}
              source={data?.sources?.insurance}
            />
            <VerifyRow
              label="Vehicle ownership / registration"
              ok={v.vehicle_verified}
              source={data?.sources?.vehicle_registration}
            />
            <VerifyRow
              label="Background check"
              ok={["passed", "cleared", "approved"].includes(
                (v.background_check_status || "").toLowerCase()
              )}
              source={data?.sources?.background_check}
              statusLabel={titleCase(v.background_check_status || "pending")}
            />
            <VerifyRow
              label="Ontario abstract"
              ok={Boolean(v.abstract_verified ?? data?.sources?.abstract?.verified)}
              source={data?.sources?.abstract}
            />
            {(v.score != null || v.quality_bonus != null) && (
              <p className="pt-2 text-xs text-muted">
                Completeness {v.score ?? 0}/4
                {v.quality_bonus ? ` · Auto quality +${v.quality_bonus}` : ""}
              </p>
            )}
          </div>
        </SectionCard>
        <SectionCard title="Expiry reminders">
          <div className="divide-y divide-primary/5">
            {expiries.map((e, i) => {
              // eslint-disable-next-line react-hooks/purity -- relative "expiring soon" check needs the current time at render
              const soon = new Date(e.expires_at) <= new Date(Date.now() + 30 * 86400000);
              return (
                <div key={i} className="flex items-center justify-between px-5 py-3">
                  <span className="text-sm text-primary">{e.label}</span>
                  <Badge tone={soon ? "red" : "slate"}>{shortDate(e.expires_at)}</Badge>
                </div>
              );
            })}
            {expiries.length === 0 && (
              <p className="px-5 py-8 text-center text-sm text-muted">No tracked expiries.</p>
            )}
          </div>
        </SectionCard>
      </div>

      <SectionCard
        title={`Uploaded documents (${files.length})`}
        action={<AddDriverDocumentForm driverId={id} onAdded={refreshDocs} />}
      >
        <div className="divide-y divide-primary/5">
          {files.map((file, i) => {
            const f = file as Record<string, string | boolean | null | undefined>;
            const label = (f.label as string) || titleCase(String(f.doc_type ?? "document"));
            const href = f.file_url ? String(f.file_url) : "";
            const isDataImage = href.startsWith("data:image");
            const isHttp = href.startsWith("http://") || href.startsWith("https://");
            const status = String(f.status ?? (f.verified ? "verified" : ""));
            return (
              <div
                key={String(f.id ?? i)}
                className="flex flex-wrap items-start justify-between gap-3 px-5 py-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-primary">{label}</p>
                  <p className="text-xs text-muted">
                    {titleCase(String(f.doc_type ?? ""))}
                    {f.reference_number ? ` · Ref ${f.reference_number}` : ""}
                  </p>
                  {f.notes ? <p className="mt-1 text-xs text-muted">{String(f.notes)}</p> : null}
                  {status === "rejected" && f.rejection_reason ? (
                    <p className="mt-1 text-xs text-red-700">{String(f.rejection_reason)}</p>
                  ) : null}
                  {isDataImage ? (
                    // Mobile uploads are stored as data URLs. A normal link cannot open them.
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={href}
                      alt={label}
                      className="mt-2 max-h-48 max-w-full rounded-lg border border-primary/10 object-contain"
                    />
                  ) : null}
                </div>
                <div className="flex flex-col items-end gap-1 text-xs">
                  {(() => {
                    const portalKey = String(f.doc_type ?? "")
                      .toLowerCase()
                      .replace("driver_license", "license")
                      .replace("drivers_license", "license")
                      .replace("vehicle_reg", "vehicle_registration")
                      .replace("mto_abstract", "abstract")
                      .replace("driver_abstract", "abstract");
                    const src =
                      data?.sources?.[portalKey] || data?.sources?.[String(f.doc_type ?? "")];
                    const sourceLabel = src?.source;
                    if (!sourceLabel || sourceLabel === "unknown") return null;
                    return (
                      <Badge tone={sourceLabel === "manual" ? "slate" : "green"}>
                        {sourceLabel === "rules"
                          ? "Rules"
                          : sourceLabel === "auto"
                            ? "Auto"
                            : "Manual"}
                        {src?.provider ? ` · ${String(src.provider).replace(/_/g, " ")}` : ""}
                      </Badge>
                    );
                  })()}
                  {status ? (
                    <Badge tone={status === "verified" || f.verified ? "green" : "amber"}>
                      {titleCase(status.replace(/_/g, " "))}
                    </Badge>
                  ) : null}
                  {f.expires_at && (
                    <Badge tone="slate">Expires {shortDate(String(f.expires_at))}</Badge>
                  )}
                  {isHttp ? (
                    <a
                      href={href}
                      target="_blank"
                      rel="noreferrer"
                      className="font-medium text-secondary hover:underline"
                    >
                      View file
                    </a>
                  ) : null}
                  {canWrite &&
                    [
                      "license",
                      "driver_license",
                      "drivers_license",
                      "insurance",
                      "insurance_certificate",
                      "vehicle_registration",
                      "vehicle_reg",
                      "registration",
                      "background_check",
                      "abstract",
                      "driver_abstract",
                      "mto_abstract",
                    ].includes(String(f.doc_type ?? "").toLowerCase()) && (
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="font-medium text-secondary hover:underline"
                          onClick={() => void decide(String(f.doc_type ?? ""), "verified")}
                        >
                          Verify
                        </button>
                        <button
                          type="button"
                          className="font-medium text-red-700 hover:underline"
                          onClick={() => {
                            setReasonFor(String(f.doc_type ?? ""));
                            setReason("");
                          }}
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  {reasonFor === String(f.doc_type ?? "") && (
                    <form
                      className="mt-1 flex gap-1"
                      onSubmit={(e) => {
                        e.preventDefault();
                        if (!reason.trim()) return;
                        void decide(String(f.doc_type ?? ""), "rejected", reason.trim());
                      }}
                    >
                      <input
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        placeholder="Reason"
                        className="rounded-lg border border-primary/15 px-2 py-1 text-xs"
                      />
                      <button type="submit" className="text-xs font-medium text-red-700">
                        Send
                      </button>
                    </form>
                  )}
                  {f.uploaded_at && (
                    <span className="text-muted">Added {shortDate(String(f.uploaded_at))}</span>
                  )}
                </div>
              </div>
            );
          })}
          {files.length === 0 && (
            <p className="px-5 py-10 text-center text-sm text-muted">
              No documents on file yet. Use Add document to attach license, insurance, or compliance
              records.
            </p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function VerifyRow({
  label,
  ok,
  source,
  statusLabel,
}: {
  label: string;
  ok: boolean;
  source?: {
    source: string;
    provider?: string | null;
  };
  statusLabel?: string;
}) {
  const sourceTone =
    source?.source === "auto" || source?.source === "rules"
      ? "green"
      : source?.source === "manual"
        ? "slate"
        : "amber";
  const sourceText =
    source?.source === "auto"
      ? "Auto"
      : source?.source === "rules"
        ? "Rules"
        : source?.source === "manual"
          ? "Manual"
          : null;
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <span className="text-sm text-primary">{label}</span>
      <div className="flex flex-wrap items-center justify-end gap-1">
        {sourceText && ok && (
          <Badge tone={sourceTone}>
            {sourceText}
            {source?.provider ? ` · ${String(source.provider).replace(/_/g, " ")}` : ""}
          </Badge>
        )}
        <Badge tone={ok ? "green" : "amber"}>{statusLabel ?? (ok ? "Verified" : "Pending")}</Badge>
      </div>
    </div>
  );
}
