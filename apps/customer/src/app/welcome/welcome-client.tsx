"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@porterchain/auth/oidc/client";
import { isAuthConfigured } from "@/lib/env";

/**
 * Landing from the booking email (L36). We hand the guest's email to Keycloak as a login hint;
 * Keycloak verifies them (password, passkey, Google/Apple) and returns them to Orders.
 */
export default function WelcomeClient() {
  const params = useSearchParams();
  const router = useRouter();
  const email = params.get("email") ?? "";
  if (!isAuthConfigured()) {
    return <Shell state="fallback" onContinue={() => router.replace("/orders")} />;
  }
  return <Redeem email={email} />;
}

function Redeem({ email }: { email: string }) {
  const { isLoaded, isSignedIn, signIn } = useAuth();
  const router = useRouter();
  const ran = useRef(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!isLoaded || ran.current) return;
    ran.current = true;
    if (isSignedIn) {
      router.replace("/orders");
      return;
    }
    try {
      signIn({ returnTo: "/orders", loginHint: email || undefined });
    } catch {
      setFailed(true);
    }
  }, [email, isLoaded, isSignedIn, router, signIn]);

  return <Shell state={failed ? "expired" : "working"} />;
}

function Shell({
  state,
  onContinue,
}: {
  state: "working" | "expired" | "fallback";
  onContinue?: () => void;
}) {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-white px-6">
      <div className="w-full max-w-sm text-center">
        <p className="text-[13px] font-semibold uppercase tracking-[0.18em] text-primary/65">
          PorterChain
        </p>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-primary" aria-live="polite">
          {state === "working"
            ? "Signing you in…"
            : state === "expired"
              ? "This link has expired"
              : "Welcome"}
        </h1>
        {state === "expired" ? (
          <Link
            href="/sign-in?redirect_url=/orders"
            className="mt-6 inline-flex w-full justify-center rounded-2xl bg-primary px-6 py-4 font-bold text-white"
          >
            Sign in
          </Link>
        ) : null}
        {state === "fallback" ? (
          <button
            type="button"
            onClick={onContinue}
            className="mt-6 inline-flex w-full justify-center rounded-2xl bg-primary px-6 py-4 font-bold text-white"
          >
            See my orders
          </button>
        ) : null}
      </div>
    </main>
  );
}
