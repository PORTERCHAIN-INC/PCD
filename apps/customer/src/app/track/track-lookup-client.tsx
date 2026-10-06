"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import CustomerMotion from "@/components/motion/CustomerMotion";

export default function TrackLookupClient() {
  const router = useRouter();
  const [value, setValue] = useState("");

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const tracking = value.trim();
    if (!tracking) return;
    router.push(`/track/${encodeURIComponent(tracking)}`);
  }

  return (
    <div className="mx-auto max-w-lg">
      <Link href="/dashboard" className="text-sm font-medium text-secondary hover:underline">
        ← Back to dashboard
      </Link>
      <CustomerMotion name="shipment" size={150} />
      <h1 className="mt-2 text-2xl font-semibold tracking-tight text-primary">Track a shipment</h1>
      <p className="mt-2 text-sm text-muted">
        Enter the tracking number from your booking confirmation or invoice.
      </p>
      <form onSubmit={onSubmit} className="mt-6 space-y-3">
        <label className="block text-xs font-semibold uppercase tracking-[0.14em] text-muted">
          Tracking number
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="e.g. PC-…"
            autoComplete="off"
            className="mt-2 w-full rounded-xl border border-primary/10 bg-white px-4 py-3 font-mono text-sm text-primary outline-none ring-secondary/30 focus:ring-2"
          />
        </label>
        <button
          type="submit"
          disabled={!value.trim()}
          className="inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-secondary px-5 text-sm font-semibold text-white hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto sm:min-w-[12rem]"
        >
          Track shipment
        </button>
      </form>
    </div>
  );
}
