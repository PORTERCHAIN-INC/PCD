"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { SignIn, useAuth, useUser } from "@clerk/nextjs";
import {
  PortalAuthScreen,
  platformLoginUrl,
  porterchainClerkAppearanceInviteOnly,
  safeAppRedirect,
} from "@porterchain/auth";
import { isClerkConfigured, isDevEmailLogin, publicEnv } from "@/lib/env";

type DevDriver = { driver_id: string; email: string; full_name: string };

function DevEmailLogin({ redirectUrl }: { redirectUrl: string }) {
  const router = useRouter();
  const [drivers, setDrivers] = useState<DevDriver[]>([]);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const res = await fetch("/api/auth/driver-dev-session");
      if (!res.ok) return;
      const rows = (await res.json()) as DevDriver[];
      setDrivers(Array.isArray(rows) ? rows : []);
      if (rows[0]?.email) setEmail(rows[0].email);
    })();
  }, []);

  async function submit(nextEmail?: string) {
    const chosen = (nextEmail ?? email).trim().toLowerCase();
    if (!chosen) {
      setError("email_required");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/driver-dev-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: chosen }),
      });
      const body = (await res.json().catch(() => ({}))) as { detail?: string };
      if (!res.ok) {
        throw new Error(typeof body.detail === "string" ? body.detail : "login_failed");
      }
      router.replace(redirectUrl);
    } catch (e) {
      setError(e instanceof Error ? e.message : "login_failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-center text-xs text-muted">
        Local email login (API <code className="text-[11px]">CLERK_DEV_BYPASS</code>). Production
        uses Clerk invitation only.
      </p>
      {drivers.length > 0 ? (
        <div className="space-y-2">
          {drivers.map((d) => (
            <button
              key={d.driver_id}
              type="button"
              disabled={busy}
              onClick={() => void submit(d.email)}
              className="flex w-full flex-col rounded-xl border border-border bg-white px-4 py-3 text-left hover:border-secondary disabled:opacity-60"
            >
              <span className="text-sm font-semibold text-primary">{d.full_name}</span>
              <span className="text-xs text-muted">{d.email}</span>
            </button>
          ))}
        </div>
      ) : (
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="driver@porterchain.com"
            className="w-full rounded-xl border border-border px-3 py-2 text-sm"
            required
          />
          <button
            type="submit"
            disabled={busy}
            className="flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white hover:bg-[#1d4ed8] disabled:opacity-60"
          >
            {busy ? "Signing in…" : "Continue"}
          </button>
        </form>
      )}
      {error ? (
        <p className="text-center text-xs text-red-600" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function ClerkDriverContinue({ redirectUrl }: { redirectUrl: string }) {
  const router = useRouter();
  const { isSignedIn, isLoaded } = useAuth();
  const { user } = useUser();
  const [continuing, setContinuing] = useState(false);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    if (!user?.primaryEmailAddress?.emailAddress) return;
    setContinuing(true);
    router.replace(redirectUrl);
  }, [isLoaded, isSignedIn, redirectUrl, router, user]);

  if (!isLoaded) {
    return (
      <p className="text-center text-sm text-muted" role="status">
        Loading sign-in…
      </p>
    );
  }

  if (isSignedIn) {
    return (
      <p className="text-center text-sm text-muted" role="status">
        {continuing ? "Opening driver portal…" : "Preparing…"}
      </p>
    );
  }

  return (
    <SignIn
      routing="path"
      path="/login"
      signUpUrl={undefined}
      forceRedirectUrl={redirectUrl}
      fallbackRedirectUrl={redirectUrl}
      appearance={porterchainClerkAppearanceInviteOnly}
    />
  );
}

function LoginPageContent() {
  const searchParams = useSearchParams();
  const redirectUrl = safeAppRedirect(searchParams.get("redirect_url"), {
    fallback: "/onboarding",
    blockPrefixes: ["/login", "/sign-in", "/sign-up"],
  });
  const showDevEmail = isDevEmailLogin();

  if (!isClerkConfigured() && !showDevEmail) {
    const platformUrl = platformLoginUrl(publicEnv.websiteUrl);
    return (
      <PortalAuthScreen
        portalLabel="Driver"
        title="Local development"
        subtitle="Clerk is not configured for this environment."
        unavailable={
          <>
            <h1 className="text-xl font-semibold text-primary">Driver portal</h1>
            <p className="mt-2 text-sm text-muted">
              Configure Clerk keys to enable driver sign-in.
            </p>
            <a
              href={platformUrl}
              className="mt-6 flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white hover:bg-[#1d4ed8]"
            >
              Platform login
            </a>
          </>
        }
      />
    );
  }

  return (
    <PortalAuthScreen
      portalLabel="Driver"
      title="Driver sign-in"
      subtitle={
        showDevEmail
          ? "Local email picker or Clerk invitation for approved partners."
          : "Invitation-only access for approved vehicle partners."
      }
      websiteUrl={publicEnv.websiteUrl}
      showPlatformLogin
      footer={
        <>Need access? Contact Porterchain operations after your partner application is approved.</>
      }
    >
      <div className="space-y-8">
        {showDevEmail ? <DevEmailLogin redirectUrl={redirectUrl} /> : null}
        {isClerkConfigured() ? (
          <>
            {showDevEmail ? (
              <p className="text-center text-xs font-medium uppercase tracking-wide text-muted">
                or Clerk invite
              </p>
            ) : null}
            <ClerkDriverContinue redirectUrl={redirectUrl} />
          </>
        ) : null}
      </div>
    </PortalAuthScreen>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <PortalAuthScreen portalLabel="Driver" title="Loading" subtitle="Preparing sign-in…">
          <p className="text-center text-sm text-muted">Loading…</p>
        </PortalAuthScreen>
      }
    >
      <LoginPageContent />
    </Suspense>
  );
}
