"use client";

import { useEffect, useState } from "react";
import { useLocale } from "next-intl";
import { formatPrice } from "@porterchain/types/booking";
import { expressConfirmation, syncCheckout, type ExpressConfirmation } from "@/lib/api";

const COPY = {
  en: {
    received: "Payment received",
    confirming: "Confirming your booking…",
    seconds: "This takes a few seconds.",
    booked: "Booked",
    title: "You\u2019re on the road.",
    lead: "Tracking, receipt and a one-tap sign-in link are on their way to your email. No password needed.",
    tracking: "Tracking number",
    paid: (v: string) => `Paid ${v} incl. HST`,
    took: (n: number) => `Booked in ${n} seconds.`,
    track: "Track live",
    receipt: "Receipt",
  },
  fr: {
    received: "Paiement reçu",
    confirming: "Confirmation de votre réservation…",
    seconds: "Quelques secondes.",
    booked: "Réservé",
    title: "C\u2019est parti.",
    lead: "Le suivi, le reçu et un lien de connexion en un clic arrivent par courriel. Aucun mot de passe.",
    tracking: "Numéro de suivi",
    paid: (v: string) => `Payé ${v} TVH incluse`,
    took: (n: number) => `Réservé en ${n} secondes.`,
    track: "Suivre en direct",
    receipt: "Reçu",
  },
};

export default function BookSuccess({ quoteId }: { quoteId: string }) {
  const locale = useLocale() === "fr" ? "fr" : "en";
  const c = COPY[locale];
  const [data, setData] = useState<ExpressConfirmation | null>(null);
  const [seconds, setSeconds] = useState<number | null>(null);

  useEffect(() => {
    if (!quoteId) return;
    let stop = false;
    let tries = 0;
    async function poll() {
      tries += 1;
      try {
        if (tries === 2) await syncCheckout(quoteId).catch(() => undefined);
        const res = await expressConfirmation(quoteId);
        if (stop) return;
        if (res.status === "ready") {
          setData(res);
          try {
            const started = Number(sessionStorage.getItem("pc_book_started") || 0);
            if (started) setSeconds(Math.round((Date.now() - started) / 1000));
            sessionStorage.removeItem("pc_book_started");
          } catch {
            /* ignore */
          }
          return;
        }
      } catch {
        /* keep polling */
      }
      if (!stop && tries < 30) window.setTimeout(poll, 1500);
    }
    void poll();
    return () => {
      stop = true;
    };
  }, [quoteId]);

  if (!data) {
    return (
      <div className="mx-auto max-w-xl" role="status" aria-live="polite">
        <p className="text-[13px] font-semibold uppercase tracking-[0.18em] text-primary/65">
          {c.received}
        </p>
        <h1 className="mt-2 text-4xl font-extrabold tracking-tight text-primary">{c.confirming}</h1>
        <p className="mt-3 text-primary/75">{c.seconds}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl">
      <p className="text-[13px] font-semibold uppercase tracking-[0.18em] text-emerald-800">
        {c.booked}
      </p>
      <h1 className="mt-2 text-4xl font-extrabold tracking-tight text-primary sm:text-5xl">
        {c.title}
      </h1>
      <p className="mt-3 text-base text-primary/75">{c.lead}</p>
      <div className="mt-8 rounded-3xl bg-primary p-6 text-white">
        <p className="text-xs font-semibold uppercase tracking-wide text-white/75">{c.tracking}</p>
        <p
          className="mt-1 font-mono text-3xl font-bold tracking-tight"
          data-testid="success-tracking"
        >
          {data.tracking_number}
        </p>
        {data.amount_cents != null ? (
          <p className="mt-2 text-sm text-white/85">
            {c.paid(formatPrice(data.amount_cents, locale))}
          </p>
        ) : null}
        {seconds != null ? (
          <p className="mt-1 text-sm text-white/85" data-testid="success-seconds">
            {c.took(seconds)}
          </p>
        ) : null}
      </div>
      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {data.manage_track_url ? (
          <a
            href={data.manage_track_url.replace("/en/track/", `/${locale}/track/`)}
            className="rounded-2xl bg-primary px-5 py-4 text-center text-base font-bold text-white shadow-lg shadow-primary/20"
          >
            {c.track}
          </a>
        ) : null}
        {data.receipt_url ? (
          <a
            href={data.receipt_url}
            className="rounded-2xl border border-primary/20 px-5 py-4 text-center text-base font-bold text-primary"
            rel="noopener noreferrer"
            target="_blank"
          >
            {c.receipt}
          </a>
        ) : null}
      </div>
    </div>
  );
}
