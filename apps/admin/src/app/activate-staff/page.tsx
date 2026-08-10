"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { publicEnv } from "@/lib/env";
import { setStaffBearer } from "@/lib/staff-session";

export default function ActivateStaffPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center bg-gray-bg p-6 text-sm text-muted">
          Activating staff access…
        </main>
      }
    >
      <ActivateStaffInner />
    </Suspense>
  );
}

function ActivateStaffInner() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token")?.trim() ?? "";
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setError("missing_enrollment_token");
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const peek = await fetch(
          `${publicEnv.porterchainApiUrl}/v1/auth/staff/enrollment/${encodeURIComponent(token)}`,
          { credentials: "include" }
        );
        if (peek.ok) {
          const data = (await peek.json()) as { email?: string };
          if (!cancelled) setEmail(data.email ?? null);
        }
        const res = await fetch(
          `${publicEnv.porterchainApiUrl}/v1/auth/staff/enrollment/${encodeURIComponent(token)}/activate`,
          { method: "POST", credentials: "include" }
        );
        const body = (await res.json().catch(() => ({}))) as {
          detail?: string;
          bearer_token?: string;
          email?: string;
        };
        if (!res.ok) {
          throw new Error(typeof body.detail === "string" ? body.detail : "activation_failed");
        }
        if (body.bearer_token) {
          setStaffBearer(body.bearer_token);
          await fetch("/api/auth/staff-session", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bearer_token: body.bearer_token }),
          });
        }
        if (!cancelled) {
          setEmail(body.email ?? null);
          router.replace("/dashboard");
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "activation_failed");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router, token]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 bg-gray-bg p-6">
      <h1 className="text-lg font-semibold text-primary">Staff activation</h1>
      {error ? (
        <p className="max-w-md text-center text-sm text-red-600">{error}</p>
      ) : (
        <p className="text-sm text-muted">
          {email ? `Activating ${email}…` : "Activating staff access…"}
        </p>
      )}
      {error && (
        <Link href="/sign-in" className="text-sm text-secondary underline">
          Back to sign-in
        </Link>
      )}
    </main>
  );
}
