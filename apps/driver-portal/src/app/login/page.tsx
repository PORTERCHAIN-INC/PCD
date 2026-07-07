"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { SignIn, useAuth, useClerk, useUser } from "@clerk/nextjs";
import { driverApi } from "@/lib/api";
import { isClerkConfigured, isDevEmailLogin } from "@/lib/env";

const DEV_DRIVER_EMAILS = [
  "marco@porterchain.com",
  "aisha@porterchain.com",
  "liam@porterchain.com",
  "priya.sharma@porterchain.com",
  "jordan.patel@porterchain.com",
  "sam.nguyen@porterchain.com",
  "elena.vasquez@porterchain.com",
  "devon.clark@porterchain.com",
];

function postLoginPath(redirectUrl: string | null): string {
  if (redirectUrl && redirectUrl !== "/" && redirectUrl.startsWith("/")) {
    return redirectUrl;
  }
  return "/onboarding";
}

function ClerkDriverExchange({ redirectUrl }: { redirectUrl: string | null }) {
  const router = useRouter();
  const { isSignedIn, isLoaded, getToken } = useAuth();
  const { signOut } = useClerk();
  const { user } = useUser();
  const [error, setError] = useState("");
  const [exchanging, setExchanging] = useState(false);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    const email = user?.primaryEmailAddress?.emailAddress;
    if (!email) return;

    let cancelled = false;
    setExchanging(true);
    setError("");

    (async () => {
      try {
        const clerkToken = await getToken();
        await driverApi.login(email, clerkToken ?? undefined);
        router.replace(postLoginPath(redirectUrl));
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "login_failed");
          setExchanging(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [getToken, isLoaded, isSignedIn, redirectUrl, router, user]);

  if (!isLoaded) {
    return (
      <div className="w-full rounded-2xl bg-white p-8 text-center shadow-sm">
        <p className="text-sm text-[var(--muted)]">Loading sign-in…</p>
      </div>
    );
  }

  if (isSignedIn) {
    return (
      <div className="w-full rounded-2xl bg-white p-8 shadow-sm">
        {exchanging && !error ? (
          <p className="text-sm text-[var(--muted)]">Linking your driver account…</p>
        ) : null}
        {error ? (
          <div className="space-y-4">
            <p className="text-sm text-red-600">{error}</p>
            <p className="text-sm text-[var(--muted)]">
              Signed in as <strong>{user?.primaryEmailAddress?.emailAddress ?? "unknown"}</strong>.
              This account is not an approved driver, or you are signed into the wrong Clerk session
              (e.g. admin).
            </p>
            <button
              type="button"
              onClick={() => signOut({ redirectUrl: "/login" })}
              className="w-full rounded-xl border border-[var(--secondary)] py-3 text-sm font-semibold text-[var(--secondary)]"
            >
              Sign out and try another account
            </button>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="w-full rounded-2xl bg-white p-4 shadow-sm">
      <SignIn
        routing="hash"
        signUpUrl={undefined}
        fallbackRedirectUrl={postLoginPath(redirectUrl)}
        appearance={{
          elements: {
            rootBox: "w-full",
            card: "shadow-none border-0",
            footerAction: { display: "none" },
          },
        }}
      />
    </div>
  );
}

function EmailDevLogin({ redirectUrl }: { redirectUrl: string | null }) {
  const router = useRouter();
  const [email, setEmail] = useState(DEV_DRIVER_EMAILS[0]);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await driverApi.login(email);
      router.replace(postLoginPath(redirectUrl));
    } catch (err) {
      setError(err instanceof Error ? err.message : "login_failed");
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="w-full rounded-2xl bg-white p-8 shadow-sm">
      <h2 className="text-lg font-semibold">Dev sign-in</h2>
      <p className="mt-1 text-sm text-[var(--muted)]">
        Email only — no password required locally. API must have{" "}
        <code className="rounded bg-[var(--gray-bg)] px-1">CLERK_DEV_BYPASS=true</code>.
      </p>
      <label className="mt-6 block text-sm font-medium" htmlFor="driver-email">
        Driver email
      </label>
      <select
        id="driver-email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="mt-2 w-full rounded-xl border px-4 py-3"
      >
        {DEV_DRIVER_EMAILS.map((addr) => (
          <option key={addr} value={addr}>
            {addr}
          </option>
        ))}
      </select>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={submitting}
        className="mt-4 w-full rounded-xl bg-[var(--secondary)] py-3 font-semibold text-white disabled:opacity-60"
      >
        {submitting ? "Signing in…" : "Sign in"}
      </button>
      <p className="mt-4 text-xs text-[var(--muted)]">
        Test accounts are seeded via{" "}
        <code className="rounded bg-[var(--gray-bg)] px-1">scripts/seed_dev_portal_users.py</code>
      </p>
    </form>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-[var(--gray-bg)] p-6">
          <p className="text-sm text-[var(--muted)]">Loading…</p>
        </div>
      }
    >
      <LoginPageContent />
    </Suspense>
  );
}

function LoginPageContent() {
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect_url");
  const showDevLogin = isDevEmailLogin();

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--gray-bg)] p-6">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-xl font-bold">Porterchain Driver</h1>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {showDevLogin
              ? "Local development — pick a seeded driver email below"
              : isClerkConfigured()
                ? "Sign in with your approved driver account"
                : "Clerk not configured — email-only dev login"}
          </p>
        </div>

        {showDevLogin ? <EmailDevLogin redirectUrl={redirectUrl} /> : null}

        {isClerkConfigured() && !showDevLogin ? (
          <ClerkDriverExchange redirectUrl={redirectUrl} />
        ) : null}

        {showDevLogin && isClerkConfigured() ? (
          <details className="rounded-2xl bg-white p-4 text-sm shadow-sm">
            <summary className="cursor-pointer font-medium">Or sign in with Clerk</summary>
            <div className="mt-4">
              <ClerkDriverExchange redirectUrl={redirectUrl} />
            </div>
          </details>
        ) : null}

        {!showDevLogin && !isClerkConfigured() ? <EmailDevLogin redirectUrl={redirectUrl} /> : null}
      </div>
    </div>
  );
}
