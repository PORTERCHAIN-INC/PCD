"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { SignIn, useAuth, useClerk } from "@clerk/nextjs";
import { Shield } from "lucide-react";
import { isClerkConfigured } from "@/lib/env";

export default function SignInPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-gray-bg">
          <p className="text-sm text-muted">Loading…</p>
        </div>
      }
    >
      <SignInGate />
    </Suspense>
  );
}

function SignInGate() {
  if (!isClerkConfigured()) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-bg p-4">
        <div className="w-full max-w-md rounded-2xl border border-primary/10 bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-bold text-primary">Porterchain Admin</h1>
          <p className="mt-2 text-sm text-muted">
            Clerk is not configured. Local dev uses API bypass — add staff in{" "}
            <code className="rounded bg-gray-bg px-1">admin_users</code> for production-like
            testing.
          </p>
          <Link
            href="/dashboard"
            className="mt-6 flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white hover:bg-secondary/90"
          >
            Continue in dev mode
          </Link>
        </div>
      </div>
    );
  }
  return <SignInContent />;
}

function resolvePostSignInTarget(raw: string | null): string {
  const fallback = "/dashboard";
  if (!raw) return fallback;
  if (raw.startsWith("/") && !raw.startsWith("/sign-in")) return raw;
  try {
    const url = new URL(raw, "https://admin.porterchain.com");
    if (url.pathname.startsWith("/sign-in")) return fallback;
    return `${url.pathname}${url.search}${url.hash}` || fallback;
  } catch {
    return fallback;
  }
}

function SignInContent() {
  const searchParams = useSearchParams();
  const { isLoaded, isSignedIn } = useAuth();
  const { signOut } = useClerk();
  const redirectUrl = resolvePostSignInTarget(searchParams.get("redirect_url"));
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    if (!isLoaded) return;

    let cancelled = false;
    void (async () => {
      if (!isSignedIn) {
        if (!cancelled) setShowForm(true);
        return;
      }

      // Client session exists — only redirect if the server middleware agrees.
      // Mismatched CLERK_SECRET_KEY causes infinite /sign-in ↔ /dashboard flicker.
      try {
        const res = await fetch("/api/auth/session", { credentials: "include", cache: "no-store" });
        const data = (await res.json()) as { signedIn?: boolean };
        if (cancelled) return;
        if (data.signedIn) {
          window.location.assign(redirectUrl);
          return;
        }
      } catch {
        // fall through — clear stale client session
      }

      if (!cancelled) {
        await signOut({ redirectUrl: `/sign-in?redirect_url=${encodeURIComponent(redirectUrl)}` });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn, redirectUrl, signOut]);

  if (!isLoaded || !showForm) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-bg">
        <p className="text-sm text-muted">Loading…</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-bg p-4">
      <div className="mb-6 max-w-md text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary/10">
          <Shield className="h-7 w-7 text-secondary" />
        </div>
        <h1 className="text-2xl font-bold text-primary">Porterchain Admin</h1>
        <p className="mt-2 text-sm text-muted">
          Staff-only access. You must be provisioned in Admin Settings → Staff before you can use
          this console. Creating a Clerk account alone does not grant access.
        </p>
      </div>
      <SignIn
        routing="hash"
        signUpUrl="/sign-in"
        forceRedirectUrl={redirectUrl}
        fallbackRedirectUrl={redirectUrl}
        appearance={{
          elements: {
            rootBox: "w-full max-w-md",
            card: "shadow-sm",
            footerAction: { display: "none" },
            footerActionLink: { display: "none" },
          },
        }}
      />
      <p className="mt-6 max-w-sm text-center text-xs text-muted">
        Need access? Ask a super admin to add your work email to the staff list.
      </p>
    </div>
  );
}
