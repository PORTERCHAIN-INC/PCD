"use client";

import { Suspense, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { SignIn, useAuth } from "@clerk/nextjs";
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
      <SignInContent />
    </Suspense>
  );
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
  const redirectUrl = resolvePostSignInTarget(searchParams.get("redirect_url"));

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    // Hard navigation so middleware receives the Clerk session cookie. Client-side
    // router.replace() can loop back to /sign-in with an infinite Loading state.
    window.location.assign(redirectUrl);
  }, [isLoaded, isSignedIn, redirectUrl]);

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

  if (!isLoaded || isSignedIn) {
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
        routing="path"
        path="/sign-in"
        forceRedirectUrl="/dashboard"
        fallbackRedirectUrl="/dashboard"
        appearance={{
          elements: {
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
