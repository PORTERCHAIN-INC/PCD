"use client";

import { useEffect, useState } from "react";
import { clearImpersonationBearer, readImpersonationBearer } from "./impersonation";

type ImpStatus = {
  actor_email: string;
  target_email: string;
  target_label?: string;
  reason: string;
  seconds_remaining: number;
};

/** Visible break-glass banner while an audited impersonation session is active. */
export function ImpersonationBanner({
  portal,
  active = false,
}: {
  portal: "driver" | "merchant" | "customer";
  /** True when the pc_imp cookie is already set, so the bar is in the first HTML. */
  active?: boolean;
}) {
  const [status, setStatus] = useState<ImpStatus | null>(null);

  useEffect(() => {
    const token = readImpersonationBearer();
    if (!token) return;
    const api =
      process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL?.replace(/\/$/, "") || "http://localhost:8001";
    let cancelled = false;
    void fetch(`${api}/v1/auth/impersonation/me`, {
      headers: { Authorization: `Bearer ${token}`, "X-Porterchain-Portal": portal },
      cache: "no-store",
    })
      .then(async (res) => {
        if (!res.ok) {
          clearImpersonationBearer();
          if (portal === "driver") {
            await fetch("/api/auth/impersonation", { method: "DELETE" });
          }
          return;
        }
        const data = (await res.json()) as ImpStatus;
        if (!cancelled) setStatus(data);
      })
      .catch(() => {
        /* ignore network */
      });
    return () => {
      cancelled = true;
    };
  }, [portal]);

  if (!status && !active) return null;

  async function endSession() {
    const token = readImpersonationBearer();
    if (token) {
      const api =
        process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL?.replace(/\/$/, "") || "http://localhost:8001";
      await fetch(`${api}/v1/auth/impersonation/end`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => undefined);
    }
    clearImpersonationBearer();
    if (portal === "driver") {
      await fetch("/api/auth/impersonation", { method: "DELETE" }).catch(() => undefined);
    }
    window.location.href = portal === "driver" ? "/login" : "/sign-in";
  }

  return (
    <div
      role="status"
      className="sticky top-0 z-50 border-b border-amber-300 bg-amber-100 px-4 py-2 text-sm text-amber-950"
    >
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2">
        <p>
          <strong>Audited impersonation</strong>
          {status
            ? ` — staff ${status.actor_email} viewing as ${status.target_label || status.target_email}. Reason: ${status.reason}. ~${Math.max(1, Math.floor(status.seconds_remaining / 60))}m left.`
            : " — opening this session."}
        </p>
        <button
          type="button"
          className="rounded border border-amber-400 bg-white px-3 py-1 text-xs font-semibold"
          onClick={() => void endSession()}
        >
          End session
        </button>
      </div>
    </div>
  );
}
