"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PortalAuthScreen, humanAuthError, safeAppRedirect } from "@porterchain/auth";
import { publicEnv, useClerkDevApiBypass, isLocalDev } from "@/lib/env";
import { establishStaffCookie, probeStaffCookie } from "@/lib/staff-session";
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
  const localSuperAdminEnabled = useClerkDevApiBypass();
  const localDev = isLocalDev();
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
  const [canPasskey, setCanPasskey] = useState(false);

  useEffect(() => {
    setCanPasskey(passkeysSupported());
  }, []);

  useEffect(() => {
    void probeStaffCookie().then((ok) => {
      if (ok) router.replace(redirectUrl);
    });
  }, [redirectUrl, router]);

  function reportError(raw: unknown, fallback: string) {
    const msg = raw instanceof Error ? raw.message : fallback;
    if (msg === "Failed to fetch") {
      setError(
        localDev
          ? `API unreachable at ${publicEnv.porterchainApiUrl}. Start the API on port 8001, then retry.`
          : "Sign-in is temporarily unavailable. Try again shortly."
      );
      return;
    }
    setError(humanAuthError(msg, fallback));
  }

  async function finishSession(bearer: string) {
    await establishStaffCookie(bearer);
    router.replace(redirectUrl);
  }

  async function continueAsLocalSuperAdmin() {
    setBusy(true);
    setError(null);
    try {
      const url = `${publicEnv.porterchainApiUrl}/v1/auth/staff/local-session`;
      const res = await fetch(url, {
        method: "POST",
        credentials: "include",
      });
      const body = (await res.json().catch(() => ({}))) as {
        detail?: string;
        bearer_token?: string;
        role?: string;
        email?: string;
      };
      if (!res.ok || !body.bearer_token) {
        throw new Error(
          typeof body.detail === "string" ? body.detail : "local_super_admin_unavailable"
        );
      }
      await finishSession(body.bearer_token);
    } catch (e) {
      reportError(e, "local_super_admin_unavailable");
    } finally {
      setBusy(false);
    }
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
        if (localDev) {
          activateWithToken(body.enrollment_token);
          return;
        }
      }
    } catch (e) {
      reportError(e, "login_request_failed");
    } finally {
      setBusy(false);
    }
  }

  async function signInWithPasskey() {
    if (!email.trim()) {
      setError("Enter your work email first.");
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
          typeof loginBody.detail === "string"
            ? loginBody.detail
            : "Passkey sign-in failed. Try the email link."
        );
      }
      await finishSession(loginBody.bearer_token);
    } catch (e) {
      reportError(e, "passkey_login_failed");
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
      subtitle="Passkey when enrolled — email link is recovery only."
      websiteUrl={publicEnv.websiteUrl}
      footer={
        <>Need first-time access? Ask a super admin to enroll you in Settings → Users → Staff.</>
      }
    >
      <div className="space-y-5 text-sm">
        {localSuperAdminEnabled && (
          <div className="rounded-xl border border-secondary/25 bg-secondary/5 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-secondary">
              Development · Local Super Admin
            </p>
            <p className="mt-1 text-xs text-muted">
              Mints a real Staff IdP session as <strong>super_admin</strong> — same auth path as
              production (not a Bearer shortcut).
            </p>
            <button
              type="button"
              disabled={busy}
              onClick={() => void continueAsLocalSuperAdmin()}
              className="mt-3 flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white hover:bg-[#1d4ed8] disabled:opacity-50"
            >
              {busy ? "Opening session…" : "Continue as Local Super Admin"}
            </button>
          </div>
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
              placeholder="you@porterchain.com"
              autoComplete="username webauthn"
              className="w-full rounded-xl border border-primary/15 bg-gray-bg px-3 py-2.5 text-primary outline-none focus:border-secondary"
            />
          </label>
          {canPasskey && (
            <button
              type="button"
              disabled={!email.trim() || busy}
              onClick={() => void signInWithPasskey()}
              className="flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-white hover:bg-[#1d4ed8] disabled:opacity-50"
            >
              {busy ? "Waiting for passkey…" : "Sign in with passkey"}
            </button>
          )}
          <button
            type="button"
            disabled={!email.trim() || busy}
            onClick={() => void requestLogin()}
            className="flex w-full items-center justify-center rounded-xl border border-primary/15 px-4 py-3 text-sm font-semibold text-primary hover:bg-gray-bg disabled:opacity-50"
          >
            {busy ? "Sending…" : "Email activate link"}
          </button>
        </div>

        {emailSent && (
          <div className="rounded-xl border border-green-200 bg-green-50/80 p-3 text-green-950">
            <p className="font-medium">Check your email for a one-time activate link.</p>
            {localDev ? (
              <p className="mt-1 text-xs text-muted">
                Mailpit:{" "}
                <a
                  href="http://localhost:8025"
                  className="underline"
                  target="_blank"
                  rel="noreferrer"
                >
                  localhost:8025
                </a>
              </p>
            ) : null}
          </div>
        )}

        {localDev && loginToken && (
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

        {localDev && (
          <div className="border-t border-primary/10 pt-4">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
                Or paste enrollment token (local)
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
        )}

        {error && <p className="text-center text-red-600">{error}</p>}
      </div>
    </PortalAuthScreen>
  );
}
