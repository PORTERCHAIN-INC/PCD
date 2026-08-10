"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { PortalAuthScreen, safeAppRedirect } from "@porterchain/auth";
import { publicEnv, useClerkDevApiBypass } from "@/lib/env";
import { getStaffBearer, setStaffBearer } from "@/lib/staff-session";
import { credentialToJson, getPasskey, passkeysSupported } from "@/lib/staff-webauthn";

export default function SignInPage() {
  return (
    <Suspense
      fallback={
        <PortalAuthScreen portalLabel="Admin" title="Loading" subtitle="Preparing staff sign-in…">
          <p className="text-center text-sm text-muted">Loading…</p>
        </PortalAuthScreen>
      }
    >
      <StaffSignIn />
    </Suspense>
  );
}

function StaffSignIn() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const devBypass = useClerkDevApiBypass();
  const redirectUrl = safeAppRedirect(searchParams.get("redirect_url"), {
    fallback: "/dashboard",
    blockPrefixes: ["/sign-in", "/sign-up", "/activate-staff"],
  });

  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [loginToken, setLoginToken] = useState<string | null>(null);
  const [emailSent, setEmailSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Defer WebAuthn probe until after mount — window.PublicKeyCredential is SSR-false / CSR-true.
  const [canPasskey, setCanPasskey] = useState(false);

  useEffect(() => {
    setCanPasskey(passkeysSupported());
  }, []);

  useEffect(() => {
    if (getStaffBearer()) {
      router.replace(redirectUrl);
    }
  }, [redirectUrl, router]);

  async function finishSession(bearer: string) {
    setStaffBearer(bearer);
    await fetch("/api/auth/staff-session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bearer_token: bearer }),
    });
    router.replace(redirectUrl);
  }

  async function requestLogin() {
    setBusy(true);
    setError(null);
    setLoginToken(null);
    setEmailSent(false);
    try {
      const res = await fetch(`${publicEnv.porterchainApiUrl}/v1/auth/staff/login-request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });
      const body = (await res.json().catch(() => ({}))) as {
        detail?: string;
        enrollment_token?: string;
        email_sent?: boolean;
        ok?: boolean;
      };
      if (!res.ok) {
        throw new Error(typeof body.detail === "string" ? body.detail : "login_request_failed");
      }
      setEmailSent(Boolean(body.email_sent ?? true));
      if (body.enrollment_token) {
        setLoginToken(body.enrollment_token);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "login_request_failed");
    } finally {
      setBusy(false);
    }
  }

  async function signInWithPasskey() {
    if (!email.trim()) {
      setError("email_required");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const optRes = await fetch(
        `${publicEnv.porterchainApiUrl}/v1/auth/staff/passkey/login/options`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email.trim() }),
        }
      );
      const options = (await optRes.json().catch(() => ({}))) as Record<string, unknown> & {
        detail?: string;
        challenge_id?: string;
      };
      if (!optRes.ok) {
        throw new Error(
          typeof options.detail === "string" ? options.detail : "passkey_options_failed"
        );
      }
      const challengeId = String(options.challenge_id || "");
      const cred = await getPasskey(options);
      const loginRes = await fetch(`${publicEnv.porterchainApiUrl}/v1/auth/staff/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          challenge_id: challengeId,
          passkey_assertion: { credential: credentialToJson(cred) },
        }),
      });
      const loginBody = (await loginRes.json().catch(() => ({}))) as {
        detail?: string;
        bearer_token?: string;
      };
      if (!loginRes.ok || !loginBody.bearer_token) {
        throw new Error(
          typeof loginBody.detail === "string" ? loginBody.detail : "passkey_login_failed"
        );
      }
      await finishSession(loginBody.bearer_token);
    } catch (e) {
      setError(e instanceof Error ? e.message : "passkey_login_failed");
    } finally {
      setBusy(false);
    }
  }

  function activateWithToken(value: string) {
    const t = value.trim();
    if (!t) return;
    router.push(`/activate-staff?token=${encodeURIComponent(t)}`);
  }

  return (
    <PortalAuthScreen
      portalLabel="Admin"
      title="Staff sign-in"
      subtitle="Staff IdP — email magic link or passkey. No Clerk."
      websiteUrl={publicEnv.websiteUrl}
      footer={
        <>Need first-time access? Ask a super admin to enroll you in Settings → Users → Staff.</>
      }
    >
      <div className="space-y-5 text-sm">
        {devBypass && (
          <Link
            href="/dashboard"
            className="flex w-full items-center justify-center rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-950 hover:bg-amber-100"
          >
            Continue with local API bypass
          </Link>
        )}

        <div className="space-y-3">
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
              Work email
            </span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@porterchain.com"
              className="w-full rounded-xl border border-primary/15 bg-gray-bg px-3 py-2.5 text-primary outline-none focus:border-secondary"
            />
          </label>
          <button
            type="button"
            disabled={!email.trim() || busy}
            onClick={() => void requestLogin()}
            className="flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white hover:bg-[#1d4ed8] disabled:opacity-50"
          >
            {busy ? "Sending…" : "Email activate link"}
          </button>
          {canPasskey && (
            <button
              type="button"
              disabled={!email.trim() || busy}
              onClick={() => void signInWithPasskey()}
              className="flex w-full items-center justify-center rounded-xl border border-primary/15 px-4 py-3 text-sm font-semibold text-primary hover:bg-gray-bg disabled:opacity-50"
            >
              Sign in with passkey
            </button>
          )}
        </div>

        {emailSent && (
          <div className="rounded-xl border border-green-200 bg-green-50/80 p-3 text-green-950">
            <p className="font-medium">Check your email for a one-time activate link.</p>
            <p className="mt-1 text-xs text-muted">
              Local Mailpit:{" "}
              <a
                href="http://localhost:8025"
                className="underline"
                target="_blank"
                rel="noreferrer"
              >
                localhost:8025
              </a>
            </p>
          </div>
        )}

        {loginToken && (
          <div className="rounded-xl border border-primary/10 bg-gray-bg/50 p-3">
            <p className="text-xs text-muted">Local only — activate without waiting for mail:</p>
            <button
              type="button"
              className="mt-2 w-full rounded-xl bg-secondary px-4 py-2.5 text-sm font-semibold text-white"
              onClick={() => activateWithToken(loginToken)}
            >
              Activate now
            </button>
          </div>
        )}

        <div className="border-t border-primary/10 pt-4">
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
              Or paste enrollment token
            </span>
            <input
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Token from enroll / email"
              className="w-full rounded-xl border border-primary/15 bg-gray-bg px-3 py-2.5 text-primary outline-none focus:border-secondary"
            />
          </label>
          <button
            type="button"
            disabled={!token.trim()}
            onClick={() => activateWithToken(token)}
            className="mt-3 flex w-full items-center justify-center rounded-xl border border-primary/15 px-4 py-2.5 text-sm font-semibold text-primary hover:bg-gray-bg disabled:opacity-50"
          >
            Activate with token
          </button>
        </div>

        {error && <p className="text-center text-red-600">{error}</p>}
      </div>
    </PortalAuthScreen>
  );
}
