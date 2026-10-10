"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { driverApi, type GpsStatus, type MonitoringPolicy } from "@/lib/api";

/**
 * Shown once per app open when location consent is needed or the current monitoring
 * policy version is not acknowledged. Agreeing records both (timestamp + version).
 * Until the driver agrees, no location is collected.
 */
export default function DriverComplianceGate() {
  const [gps, setGps] = useState<GpsStatus | null>(null);
  const [policy, setPolicy] = useState<MonitoringPolicy | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    driverApi
      .gpsStatus()
      .then(setGps)
      .catch(() => undefined);
    driverApi
      .monitoringPolicy()
      .then(setPolicy)
      .catch(() => undefined);
  }, []);

  const needsConsent = Boolean(gps?.consent_required);
  const needsAck = policy ? !policy.acknowledged : false;
  if (dismissed || (!needsConsent && !needsAck)) return null;

  async function agree() {
    setBusy(true);
    try {
      if (needsAck) setPolicy(await driverApi.ackMonitoringPolicy());
      if (needsConsent) setGps(await driverApi.gpsConsent(true));
      setDismissed(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="compliance-gate-title"
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center"
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl">
        <h2 id="compliance-gate-title" className="text-lg font-bold text-[var(--primary)]">
          Location sharing and monitoring
        </h2>
        {needsConsent ? (
          <p className="mt-2 text-sm text-[var(--primary)]">{gps?.consent_text || gps?.message}</p>
        ) : null}
        <p className="mt-2 text-sm text-[var(--primary)]">
          {needsAck ? "Please read our Electronic Monitoring Policy. " : ""}
          <Link
            href={gps?.policy_url || "/monitoring-policy"}
            onClick={() => setDismissed(true)}
            className="font-semibold text-[var(--secondary)] underline"
          >
            Read the Electronic Monitoring Policy
          </Link>
        </p>
        {needsConsent ? (
          <p className="mt-2 text-xs text-[var(--muted)]">
            Until you agree, your location is not shared and live tracking stays off.
          </p>
        ) : null}
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void agree()}
            disabled={busy}
            className="min-h-11 flex-1 rounded-xl bg-[var(--secondary)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {busy ? "Saving…" : "I agree"}
          </button>
          <button
            type="button"
            onClick={() => setDismissed(true)}
            className="min-h-11 rounded-xl border border-[var(--primary)]/15 px-4 py-2 text-sm font-semibold text-[var(--primary)]"
          >
            Not now
          </button>
        </div>
      </div>
    </div>
  );
}
