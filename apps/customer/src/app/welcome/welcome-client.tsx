"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useSignIn } from "@clerk/nextjs";
import { isClerkConfigured } from "@/lib/env";

/**
 * One-tap sign-in from the booking email. The API mints a Clerk sign-in token for the
 * guest's email; we redeem it with the `ticket` strategy and land on Orders. No code, no password.
 */
export default function WelcomeClient() {
  const params = useSearchParams();
  const router = useRouter();
  const ticket = params.get("ticket") ?? "";
  if (!isClerkConfigured() || !ticket) {
    return <Shell state="fallback" onContinue={() => router.replace("/orders")} />;
  }
  return <Redeem ticket={ticket} />;
}

function Redeem({ ticket }: { ticket: string }) {
  const router = useRouter();
  const { signIn } = useSignIn();
  const [failed, setFailed] = useState(false);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current || !signIn) return;
    ran.current = true;
    void (async () => {
      try {
        const res = await signIn.ticket({ ticket });
        if (res?.error || signIn.status !== "complete") throw new Error("ticket");
        await signIn.finalize({
          navigate: ({ decorateUrl }) => {
            const url = decorateUrl("/orders");
            if (url.startsWith("http")) window.location.href = url;
            else router.replace(url);
          },
        });
      } catch {
        setFailed(true);
      }
    })();
  }, [signIn, ticket, router]);

  return <Shell state={failed ? "expired" : "working"} />;
}

function Shell({ state, onContinue }: { state: "working" | "expired" | "fallback"; onContinue?: () => void }) {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-white px-6">
      <div className="w-full max-w-sm text-center">
        <p className="text-[13px] font-semibold uppercase tracking-[0.18em] text-primary/65">PorterChain</p>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-primary" aria-live="polite">
          {state === "working" ? "Signing you in…" : state === "expired" ? "This link has expired" : "Welcome"}
        </h1>
        {state === "expired" ? (
          <Link href="/sign-in?redirect_url=/orders" className="mt-6 inline-flex w-full justify-center rounded-2xl bg-primary px-6 py-4 font-bold text-white">
            Get a new sign-in code
          </Link>
        ) : null}
        {state === "fallback" ? (
          <button type="button" onClick={onContinue} className="mt-6 inline-flex w-full justify-center rounded-2xl bg-primary px-6 py-4 font-bold text-white">
            See my orders
          </button>
        ) : null}
      </div>
    </main>
  );
}
