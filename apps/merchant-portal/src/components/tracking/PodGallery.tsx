"use client";

type Pod = {
  photos?: Array<Record<string, unknown>>;
  signatures?: Array<Record<string, unknown>>;
  otp?: Array<Record<string, unknown>>;
  other?: Array<Record<string, unknown>>;
  complete?: boolean;
};

export function PodGallery({ pod }: { pod: Pod }) {
  const photos = pod.photos ?? [];
  const signatures = pod.signatures ?? [];
  const otps = pod.otp ?? [];

  if (!photos.length && !signatures.length && !otps.length) {
    return <p className="text-sm text-muted">Proof of delivery will appear after completion.</p>;
  }

  return (
    <div className="space-y-6">
      {photos.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-primary">Photos</h3>
          <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {photos.map((p, i) => (
              <a
                key={i}
                href={String(p.url ?? "#")}
                target="_blank"
                rel="noopener noreferrer"
                className="block overflow-hidden rounded-xl border border-primary/10"
              >
                {p.url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={String(p.url)} alt="POD" className="h-28 w-full object-cover" />
                ) : (
                  <div className="flex h-28 items-center justify-center bg-gray-50 text-xs text-muted">Photo</div>
                )}
              </a>
            ))}
          </div>
        </section>
      )}

      {signatures.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-primary">Signature</h3>
          <ul className="mt-2 space-y-2">
            {signatures.map((s, i) => (
              <li key={i} className="rounded-xl border border-primary/10 p-3 text-sm">
                {s.url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={String(s.url)} alt="Signature" className="max-h-24" />
                ) : s.signature ? (
                  <span className="font-mono text-xs">{String(s.signature).slice(0, 120)}</span>
                ) : (
                  <span className="text-muted">Signature captured</span>
                )}
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
