"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

function UnsubscribeInner() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [status, setStatus] = useState<"idle" | "working" | "ok" | "error">("idle");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Missing unsubscribe token.");
      return;
    }
    let cancelled = false;
    setStatus("working");
    void (async () => {
      try {
        const res = await fetch("/api/leads/unsubscribe", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
        if (cancelled) return;
        if (!res.ok) {
          const body = (await res.json().catch(() => ({}))) as { error?: string };
          setStatus("error");
          setMessage(body.error ?? "Unsubscribe failed.");
          return;
        }
        setStatus("ok");
        setMessage("You have been unsubscribed from PorterChain marketing email.");
      } catch {
        if (!cancelled) {
          setStatus("error");
          setMessage("Unsubscribe failed.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <main className="mx-auto flex min-h-[50vh] max-w-lg flex-col justify-center px-6 py-16">
      <h1 className="text-2xl font-semibold text-slate-900">Email preferences</h1>
      <p className="mt-3 text-sm text-slate-600">
        {status === "working" ? "Updating your preferences…" : message}
      </p>
    </main>
  );
}

export default function UnsubscribePage() {
  return (
    <Suspense fallback={<main className="p-8 text-sm text-slate-600">Loading…</main>}>
      <UnsubscribeInner />
    </Suspense>
  );
}
