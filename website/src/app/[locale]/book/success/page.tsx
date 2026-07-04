"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";
import { getBookingConfirmation, type BookingConfirmationResult } from "@/lib/api";
import { publicEnv } from "@/lib/env";

export default function BookSuccessPage() {
  return (
    <Suspense
      fallback={
        <SiteShell>
          <Container className="py-16 md:py-24 max-w-lg text-center">
            <p className="type-small text-muted">Loading…</p>
          </Container>
        </SiteShell>
      }
    >
      <BookSuccessContent />
    </Suspense>
  );
}

function BookSuccessContent() {
  const t = useTranslations("booking.success");
  const searchParams = useSearchParams();
  const quoteId = searchParams.get("quote_id") ?? "";

  // Legacy query fallback (older links).
  const legacyTracking = searchParams.get("tracking") ?? "";

  const [confirmation, setConfirmation] = useState<BookingConfirmationResult | null>(null);
  const [processing, setProcessing] = useState(Boolean(quoteId));
  const [timedOut, setTimedOut] = useState(false);

  // Poll for the confirmation — the order is created by the verified Stripe webhook.
  useEffect(() => {
    if (!quoteId) return;
    let cancelled = false;
    let attempts = 0;
    const maxAttempts = 20;

    async function poll() {
      try {
        const res = await getBookingConfirmation(quoteId);
        if (cancelled) return;
        if (res.status === "ready" && res.confirmation) {
          setConfirmation(res.confirmation);
          setProcessing(false);
          return;
        }
      } catch {
        /* keep polling */
      }
      attempts += 1;
      if (attempts >= maxAttempts) {
        if (!cancelled) {
          setProcessing(false);
          setTimedOut(true);
        }
        return;
      }
      if (!cancelled) setTimeout(poll, 1500);
    }
    poll();
    return () => {
      cancelled = true;
    };
  }, [quoteId]);

  const tracking = confirmation?.tracking_number ?? legacyTracking;

  const refs = confirmation
    ? [
        { label: t("trackingLabel"), value: confirmation.tracking_number },
        { label: t("orderLabel"), value: confirmation.order_number },
        { label: t("bookingLabel"), value: confirmation.booking_number },
        { label: t("invoiceLabel"), value: confirmation.invoice_number },
        { label: "Receipt", value: confirmation.receipt_number ?? "" },
        { label: "Payment ref", value: confirmation.payment_reference ?? "" },
        { label: "Customer ref", value: confirmation.customer_reference ?? "" },
      ].filter((r) => r.value)
    : [
        { label: t("trackingLabel"), value: legacyTracking },
        { label: t("orderLabel"), value: searchParams.get("order") ?? "" },
        { label: t("bookingLabel"), value: searchParams.get("booking") ?? "" },
        { label: t("invoiceLabel"), value: searchParams.get("invoice") ?? "" },
      ].filter((r) => r.value);

  return (
    <SiteShell>
      <Container className="py-16 md:py-24 max-w-lg text-center">
        {processing ? (
          <>
            <h1 className="type-h2 font-bold text-primary mb-2">Finalizing your booking…</h1>
            <p className="type-small text-muted mb-6">
              We&apos;re confirming your payment securely. This takes a few seconds.
            </p>
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-secondary/30 border-t-secondary" />
          </>
        ) : (
          <>
            <h1 className="type-h2 font-bold text-primary mb-2">{t("title")}</h1>
            <p className="type-small text-muted mb-6">{t("subtitle")}</p>

            {timedOut && !confirmation && (
              <p className="type-small text-amber-700 mb-6">
                Payment received — your booking is being finalized. Check your dashboard shortly.
              </p>
            )}

            {refs.length > 0 && (
              <dl className="text-left rounded-2xl bg-gray-bg p-4 mb-4 space-y-2">
                {refs.map((r) => (
                  <div key={r.label} className="flex justify-between gap-4">
                    <dt className="type-caption text-muted">{r.label}</dt>
                    <dd className="type-caption font-mono font-semibold text-primary">{r.value}</dd>
                  </div>
                ))}
              </dl>
            )}

            {confirmation && (
              <dl className="text-left rounded-2xl bg-gray-bg p-4 mb-8 space-y-2">
                <div className="flex justify-between gap-4">
                  <dt className="type-caption text-muted">Amount paid</dt>
                  <dd className="type-caption font-semibold text-primary">
                    ${(confirmation.amount_cents / 100).toFixed(2)}{" "}
                    {confirmation.currency.toUpperCase()}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="type-caption text-muted">Estimated pickup</dt>
                  <dd className="type-caption text-primary">
                    {new Date(confirmation.scheduled_at).toLocaleString("en-CA", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </dd>
                </div>
              </dl>
            )}

            <div className="flex flex-col gap-3">
              {confirmation?.receipt_url && (
                <a
                  href={confirmation.receipt_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center justify-center w-full min-h-[3rem] rounded-full border-2 border-secondary text-secondary font-bold type-button hover:bg-secondary/5 transition-colors"
                >
                  Download receipt
                </a>
              )}
              {tracking && (
                <Link
                  href={`/track/${tracking}`}
                  className="inline-flex items-center justify-center w-full min-h-[3rem] rounded-full bg-secondary text-white font-bold type-button hover:bg-[#1d4ed8] transition-colors"
                >
                  {t("track")}
                </Link>
              )}
              <a
                href={`${publicEnv.customerPortalUrl}/dashboard`}
                className="inline-flex items-center justify-center w-full min-h-[3rem] rounded-full border-2 border-secondary text-secondary font-bold type-button hover:bg-secondary/5 transition-colors"
              >
                {t("dashboard")}
              </a>
              <Link
                href="/#book"
                className="inline-flex items-center justify-center w-full py-3 rounded-full text-primary font-semibold type-button hover:bg-gray-bg transition-colors"
              >
                Book another delivery
              </Link>
              <Link
                href="/"
                className="inline-flex items-center justify-center w-full py-3 rounded-full text-primary font-semibold type-button hover:bg-gray-bg transition-colors"
              >
                {t("home")}
              </Link>
            </div>
          </>
        )}
      </Container>
    </SiteShell>
  );
}
