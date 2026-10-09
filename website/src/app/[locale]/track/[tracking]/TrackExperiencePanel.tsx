"use client";

import {
  etaWindowText,
  safeBrandColor,
  statusHeadline,
  stopsAwayText,
  type TrackingExperienceEnhanced,
} from "@porterchain/types";

function fmtAt(value: string | null): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("en-CA", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/Toronto",
  });
}

/** Branded recipient view — rendered only when the merchant turned the branded page on. */
export default function TrackExperiencePanel({
  exp,
  manageHref,
}: {
  exp: TrackingExperienceEnhanced;
  manageHref?: string | null;
}) {
  const brand = safeBrandColor(exp.branding.primary_color);
  const accent = safeBrandColor(exp.branding.accent_color, "#f59e0b");
  const eta = etaWindowText(exp.eta_window);
  const stops = stopsAwayText(exp.stops_away, exp.state);
  const pod = exp.proof_of_delivery;
  const help = exp.help;

  return (
    <section
      className="mb-8 overflow-hidden rounded-2xl border border-primary/10 bg-white"
      data-testid="track-experience"
    >
      <div className="flex items-center gap-3 p-5 text-white" style={{ backgroundColor: brand }}>
        {exp.branding.logo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={exp.branding.logo_url}
            alt={exp.branding.company_name ? `${exp.branding.company_name} logo` : "Sender logo"}
            referrerPolicy="no-referrer"
            className="h-12 w-12 rounded-lg bg-white object-contain"
          />
        ) : null}
        <div>
          {exp.branding.company_name ? (
            <p className="type-small opacity-90">{exp.branding.company_name}</p>
          ) : null}
          <p className="text-xl font-bold" aria-live="polite">
            {statusHeadline(exp)}
          </p>
        </div>
      </div>

      <div className="space-y-5 p-5">
        <ol className="grid grid-cols-4 gap-2" aria-label="Delivery progress">
          {exp.progress.map((step) => (
            <li key={step.code} className="text-center">
              <span
                className="mx-auto mb-1 block h-2 rounded-full"
                style={{ backgroundColor: step.done ? accent : "#e5e7eb" }}
              />
              <span className={`type-caption ${step.done ? "text-primary" : "text-muted"}`}>
                {step.label}
              </span>
            </li>
          ))}
        </ol>

        {eta || stops || exp.driver?.name ? (
          <dl className="space-y-2 rounded-xl bg-gray-bg p-4">
            {eta ? (
              <div className="flex justify-between gap-4">
                <dt className="type-small text-muted">Delivery window</dt>
                <dd className="type-small text-right font-semibold">{eta}</dd>
              </div>
            ) : null}
            {stops ? (
              <div className="flex justify-between gap-4">
                <dt className="type-small text-muted">Driver</dt>
                <dd className="type-small text-right font-semibold">{stops}</dd>
              </div>
            ) : null}
            {exp.driver?.name ? (
              <div className="flex justify-between gap-4">
                <dt className="type-small text-muted">Your driver</dt>
                <dd className="type-small text-right">{exp.driver.name}</dd>
              </div>
            ) : null}
          </dl>
        ) : null}

        {exp.rules.id_required || exp.rules.signature_required ? (
          <p className="type-small rounded-xl border border-amber-200 bg-amber-50 p-3">
            {exp.rules.id_required ? "Photo ID is required at delivery. " : ""}
            {exp.rules.signature_required ? "Someone must be there to sign." : ""}
          </p>
        ) : null}

        {exp.attempts > 0 && !pod ? (
          <p className="type-small text-red-700">
            {exp.returning_to_sender
              ? "We could not deliver after repeated attempts, so the parcel is going back to the sender."
              : `We tried to deliver ${exp.attempts === 1 ? "once" : `${exp.attempts} times`}.`}
          </p>
        ) : null}

        {pod ? (
          <div
            className="rounded-xl border border-green-200 bg-green-50 p-4"
            data-testid="track-pod"
          >
            <p className="type-small font-semibold text-green-900">
              Delivered {fmtAt(pod.delivered_at)}
            </p>
            {pod.received_by ? (
              <p className="type-small text-green-900">Received by {pod.received_by}</p>
            ) : null}
            {pod.proof_types.length ? (
              <p className="type-caption text-green-900">Proof: {pod.proof_types.join(", ")}</p>
            ) : null}
            {pod.photos.map((src) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={src}
                src={src}
                alt="Proof of delivery"
                referrerPolicy="no-referrer"
                className="mt-3 w-full rounded-lg"
              />
            ))}
          </div>
        ) : null}

        {exp.timeline.length ? (
          <ol className="space-y-2 border-l-2 border-primary/10 pl-4" aria-label="Delivery history">
            {exp.timeline
              .slice()
              .reverse()
              .map((item, i) => (
                <li key={`${item.code}-${i}`} className="type-small">
                  <span className="font-semibold">{item.label}</span>{" "}
                  <span className="text-muted">{fmtAt(item.at)}</span>
                </li>
              ))}
          </ol>
        ) : null}

        {exp.self_service.available ? (
          manageHref ? (
            <a
              href={manageHref}
              className="inline-flex rounded-xl px-4 py-2.5 font-semibold text-white type-small"
              style={{ backgroundColor: brand }}
            >
              Change delivery time or add instructions
            </a>
          ) : (
            <p className="type-small text-muted">
              To change the delivery time or add a gate code, use the link in your delivery message.
            </p>
          )
        ) : null}

        {help.email || help.phone || help.url ? (
          <div className="type-small text-muted">
            Need help?{" "}
            {help.email ? (
              <a className="underline" href={`mailto:${help.email}`}>
                {help.email}
              </a>
            ) : null}
            {help.email && help.phone ? " · " : null}
            {help.phone ? (
              <a className="underline" href={`tel:${help.phone.replace(/[^+0-9]/g, "")}`}>
                {help.phone}
              </a>
            ) : null}
            {(help.email || help.phone) && help.url ? " · " : null}
            {help.url ? (
              <a className="underline" href={help.url} rel="noopener noreferrer" target="_blank">
                Help centre
              </a>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}
