"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { syncBookingCheckout, type BookingConfirmation } from "@/lib/booking";

function SuccessContent() {
  const searchParams = useSearchParams();
  const quoteId = searchParams.get("quote_id") ?? "";
  const [confirmation, setConfirmation] = useState<BookingConfirmation | null>(null);
  const [processing, setProcessing] = useState(Boolean(quoteId));
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    if (!quoteId) return;
    let cancelled = false;
    let attempts = 0;
    const maxAttempts = 20;

    async function poll() {
      try {
        const res = await syncBookingCheckout(quoteId);
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

  if (!quoteId) {
    return (
      <div className="mx-auto max-w-lg rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900">Missing booking reference</h1>
        <p className="mt-2 text-sm text-slate-600">Return to booking and try again.</p>
        <Link href="/book" className="mt-6 inline-block text-sm font-semibold text-emerald-700 hover:underline">
          Back to book
        </Link>
      </div>
    );
  }

  if (processing) {
    return (
      <div className="mx-auto max-w-lg rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900">Finalizing your booking…</h1>
        <p className="mt-2 text-sm text-slate-600">Confirming payment with Stripe.</p>
      </div>
    );
  }

  if (timedOut && !confirmation) {
    return (
      <div className="mx-auto max-w-lg rounded-2xl border border-amber-200 bg-white p-8 text-center shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900">Still processing</h1>
        <p className="mt-2 text-sm text-slate-600">
          Payment may still be confirming. Check your dashboard in a few minutes.
        </p>
        <Link href="/dashboard" className="mt-6 inline-block text-sm font-semibold text-emerald-700 hover:underline">
          Go to dashboard
        </Link>
      </div>
    );
  }

  const tracking = confirmation?.tracking_number ?? "";

  return (
    <div className="mx-auto max-w-lg rounded-2xl border border-emerald-200 bg-white p-8 text-center shadow-sm">
      <h1 className="text-2xl font-bold text-slate-900">Booking confirmed</h1>
      <p className="mt-2 text-sm text-slate-600">Your delivery is booked.</p>
      {tracking ? (
        <>
          <p className="mt-6 font-mono text-lg font-semibold text-emerald-800">{tracking}</p>
          <p className="mt-1 text-xs text-slate-500">Tracking number</p>
        </>
      ) : null}
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        {tracking ? (
          <Link
            href={`/track/${encodeURIComponent(tracking)}`}
            className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800"
          >
            Track delivery
          </Link>
        ) : null}
        <Link href="/dashboard" className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
          Dashboard
        </Link>
      </div>
    </div>
  );
}

export default function BookSuccessPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-lg py-16 text-center text-sm text-slate-600">Loading…</div>
      }
    >
      <SuccessContent />
    </Suspense>
  );
}
