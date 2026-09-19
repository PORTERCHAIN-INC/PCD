"use client";

import { useState } from "react";
import { downloadMerchantFile, ordersApi } from "@/lib/orders";

type Proof = {
  url?: unknown;
  signature?: unknown;
  otp?: unknown;
  type?: unknown;
  /** Handle the API stamps on each proof so we can ask for its bytes (BR). */
  download?: unknown;
};

type Pod = {
  photos?: Proof[];
  signatures?: Proof[];
  otp?: Proof[];
  other?: Proof[];
  complete?: boolean;
};

type Props = {
  pod: Pod;
  /** Enables downloads. Without it the gallery stays view-only. */
  orderId?: string;
  getToken?: () => Promise<string>;
  orgId?: string;
};

export function PodGallery({ pod, orderId, getToken, orgId }: Props) {
  const photos = pod.photos ?? [];
  const signatures = pod.signatures ?? [];
  const otps = pod.otp ?? [];
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canDownload = Boolean(orderId && getToken);

  async function save(path: string, fallbackName: string, key: string) {
    if (!getToken) return;
    setBusy(key);
    setError(null);
    try {
      await downloadMerchantFile(await getToken(), path, fallbackName, orgId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not download that file.");
    } finally {
      setBusy(null);
    }
  }

  function saveOne(proof: Proof, label: string) {
    const slug = String(proof.download ?? "");
    if (!orderId || !slug) return;
    // The API picks the real extension from the media type it reads.
    void save(ordersApi.podArtifactPath(orderId, slug), `${label}.jpg`, slug);
  }

  if (!photos.length && !signatures.length && !otps.length) {
    return <p className="text-sm text-muted">Proof of delivery will appear after completion.</p>;
  }

  return (
    <div className="space-y-6">
      {canDownload && (
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={busy !== null}
            onClick={() =>
              void save(ordersApi.podBundlePath(String(orderId)), "proof-of-delivery.zip", "bundle")
            }
            className="rounded-xl bg-primary px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {busy === "bundle" ? "Preparing…" : "Download all proof"}
          </button>
          <span className="text-xs text-muted">
            Photos and the signature, ready to attach to an invoice or a claim.
          </span>
        </div>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {photos.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-primary">Photos</h3>
          <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {photos.map((p, i) => (
              <figure key={i} className="overflow-hidden rounded-xl border border-primary/10">
                <a href={String(p.url ?? "#")} target="_blank" rel="noopener noreferrer">
                  {p.url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={String(p.url)} alt="POD" className="h-28 w-full object-cover" />
                  ) : (
                    <div className="flex h-28 items-center justify-center bg-gray-50 text-xs text-muted">
                      Photo
                    </div>
                  )}
                </a>
                {canDownload && p.download ? (
                  <figcaption className="border-t border-primary/10 px-2 py-1.5">
                    <button
                      type="button"
                      disabled={busy !== null}
                      onClick={() => saveOne(p, `photo-${i + 1}`)}
                      className="text-xs font-semibold text-secondary hover:underline disabled:opacity-50"
                    >
                      {busy === String(p.download) ? "Saving…" : "Download"}
                    </button>
                  </figcaption>
                ) : null}
              </figure>
            ))}
          </div>
        </section>
      )}

      {signatures.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-primary">Signature</h3>
          <ul className="mt-2 space-y-2">
            {signatures.map((s, i) => (
              <li
                key={i}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-primary/10 p-3 text-sm"
              >
                {s.url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={String(s.url)} alt="Signature" className="max-h-24" />
                ) : s.signature ? (
                  <span className="font-mono text-xs">{String(s.signature).slice(0, 120)}</span>
                ) : (
                  <span className="text-muted">Signature captured</span>
                )}
                {canDownload && s.download ? (
                  <button
                    type="button"
                    disabled={busy !== null}
                    onClick={() => saveOne(s, `signature-${i + 1}`)}
                    className="text-xs font-semibold text-secondary hover:underline disabled:opacity-50"
                  >
                    {busy === String(s.download) ? "Saving…" : "Download"}
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      )}

      {otps.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-primary">OTP / verification</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {otps.map((o, i) => (
              <li key={i} className="font-mono">
                {String(o.otp ?? o.type ?? "verified")}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
