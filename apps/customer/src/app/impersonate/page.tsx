"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { clearImpersonationBearer, storeImpersonationBearer } from "@porterchain/auth";

export default function CustomerImpersonatePage() {
  return (
    <Suspense fallback={<p className="p-8 text-sm text-muted">Preparing impersonation…</p>}>
      <ImpersonateBootstrap home="/dashboard" />
    </Suspense>
  );
}

function ImpersonateBootstrap({ home }: { home: string }) {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = params.get("token")?.trim() || "";
    if (!token.startsWith("pc_imp_")) {
      setError("invalid_impersonation_token");
      return;
    }
    storeImpersonationBearer(token);
    void fetch("/api/auth/impersonation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => ({}))) as { detail?: string };
          throw new Error(body.detail || "impersonation_bootstrap_failed");
        }
        router.replace(home);
      })
      .catch((e) => {
        clearImpersonationBearer();
        setError(e instanceof Error ? e.message : "impersonation_bootstrap_failed");
      });
  }, [home, params, router]);

  if (error) {
    return (
      <div className="mx-auto max-w-md space-y-3 p-8 text-sm">
        <p className="font-semibold text-red-700">Impersonation failed</p>
        <p className="text-muted">{error}</p>
      </div>
    );
  }
  return <p className="p-8 text-sm text-muted">Starting audited impersonation…</p>;
}
