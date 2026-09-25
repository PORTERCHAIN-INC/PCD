"use client";

import { useAdminAuth } from "@/hooks/useAdminAuth";
import type { OrderDetail } from "@/lib/orders";
import { Button } from "@/components/crm/primitives";
import { PodDownloadAll, PodDownloadOne } from "@/components/orders/PodDownloads";
import { SectionBlock } from "@/components/orders/sections";
import { Row } from "./shared";

export function DocumentsTab({
  detail,
  onDownloadRecord,
}: {
  detail: OrderDetail;
  onDownloadRecord: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-primary/10 p-4">
        <p className="text-sm text-muted">
          Shipment record includes addresses, PO and references, stops, and the activity trail.
        </p>
        <Button variant="outline" className="mt-3 px-3 py-1.5 text-sm" onClick={onDownloadRecord}>
          Download shipment record
        </Button>
      </div>
      <ul className="space-y-2">
        {detail.documents.map((d, i) => (
          <li key={i}>
            <a
              href={String(d.url)}
              target="_blank"
              rel="noreferrer"
              className="text-sm text-secondary hover:underline"
            >
              {String(d.name)} ({String(d.type)})
            </a>
          </li>
        ))}
        {!detail.documents.length && (
          <p className="text-sm text-muted">No other files attached to this order.</p>
        )}
      </ul>
    </div>
  );
}

export function PodTab({ pod, orderId }: { pod: Record<string, unknown>; orderId: string }) {
  const { getApiToken } = useAdminAuth();
  const photos = Array.isArray(pod.photos) ? (pod.photos as Array<Record<string, unknown>>) : [];
  const signatures = Array.isArray(pod.signatures)
    ? (pod.signatures as Array<Record<string, unknown>>)
    : [];
  const otps = Array.isArray(pod.otp) ? (pod.otp as Array<Record<string, unknown>>) : [];
  const hasGallery = photos.length + signatures.length + otps.length > 0;

  if (!hasGallery && !Object.keys(pod).length) {
    return (
      <div className="space-y-2">
        <p className="text-sm text-muted">Proof of delivery not yet captured</p>
        <p className="text-xs text-muted">
          Capture in the driver app / Fleetbase — Admin is read-only.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        {pod.source ? (
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted">
            Live from Fleetbase
          </p>
        ) : null}
        {hasGallery ? <PodDownloadAll orderId={orderId} getApiToken={getApiToken} /> : null}
      </div>
      {(photos.length > 0 || signatures.length > 0) && (
        <div className="flex flex-wrap gap-3">
          {photos.map((p, i) =>
            typeof p.url === "string" ? (
              <figure key={String(p.id ?? i)} className="space-y-1">
                {/* eslint-disable-next-line @next/next/no-img-element -- Fleetbase proof URL */}
                <img
                  src={p.url}
                  alt="Delivery photo"
                  className="h-36 w-36 rounded-xl border border-primary/10 object-cover"
                />
                <PodDownloadOne
                  orderId={orderId}
                  getApiToken={getApiToken}
                  slug={p.download}
                  fallbackName={`photo-${i + 1}.jpg`}
                />
              </figure>
            ) : null
          )}
          {signatures.map((s, i) => {
            const src =
              typeof s.url === "string"
                ? s.url
                : typeof s.signature === "string" && s.signature.startsWith("data:")
                  ? s.signature
                  : null;
            return src ? (
              <figure key={String(s.id ?? `sig-${i}`)} className="space-y-1">
                {/* eslint-disable-next-line @next/next/no-img-element -- Fleetbase signature */}
                <img
                  src={src}
                  alt="Recipient signature"
                  className="h-36 rounded-xl border border-primary/10 bg-gray-bg object-contain px-4"
                />
                <PodDownloadOne
                  orderId={orderId}
                  getApiToken={getApiToken}
                  slug={s.download}
                  fallbackName={`signature-${i + 1}.png`}
                />
              </figure>
            ) : null;
          })}
        </div>
      )}
      {otps.length > 0 && (
        <div className="space-y-1">
          {otps.map((o, i) => (
            <Row key={i} label="OTP / barcode" value={String(o.otp ?? o.code ?? "—")} mono />
          ))}
        </div>
      )}
      {!hasGallery && pod.event_payload ? (
        <p className="text-xs text-muted">
          POD event recorded — media not synced from Fleetbase yet.
        </p>
      ) : null}
    </div>
  );
}

export function EvidenceSection({
  detail,
  onDownloadRecord,
}: {
  detail: OrderDetail;
  onDownloadRecord: () => void;
}) {
  return (
    <div className="space-y-8">
      <SectionBlock title="Proof of delivery">
        <PodTab pod={detail.proof_of_delivery} orderId={detail.order_id} />
      </SectionBlock>
      <SectionBlock title="Documents">
        <DocumentsTab detail={detail} onDownloadRecord={onDownloadRecord} />
      </SectionBlock>
    </div>
  );
}
