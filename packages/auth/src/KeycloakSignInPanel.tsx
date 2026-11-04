"use client";

import { useEffect, useState } from "react";
import { useAuth } from "./oidc/client";

const ERRORS: Record<string, string> = {
  access_denied: "Sign-in was cancelled. Try again when you're ready.",
  state_mismatch: "That sign-in link expired. Start again.",
  login_required: "Please sign in again.",
  temporarily_unavailable: "Sign-in is briefly unavailable. Try again in a minute.",
};

export function authErrorMessage(code: string | null): string | null {
  if (!code) return null;
  return ERRORS[code] ?? "We couldn't finish signing you in. Try again.";
}

/** Social providers shown on our page; Keycloak's own page always lists every enabled IdP. */
function enabledIdps(): string[] {
  return (process.env.NEXT_PUBLIC_AUTH_IDPS ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s === "google" || s === "apple");
}

const btn =
  "flex h-11 w-full items-center justify-center rounded-xl text-sm font-semibold transition disabled:opacity-60";

/**
 * Keycloak sign-in / sign-up entry (L36): primary button to the hosted page plus optional
 * Google / Apple shortcuts (kc_idp_hint). Passwords, passkeys and MFA live on Keycloak.
 */
export function KeycloakSignInPanel({
  mode = "sign-in",
  returnTo,
  loginHint,
  primaryLabel,
  autoRedirect = true,
}: {
  mode?: "sign-in" | "sign-up";
  returnTo: string;
  loginHint?: string;
  primaryLabel?: string;
  /** One-step sign-in (previous provider feel): open the Keycloak form straight away. The button stays as fallback
   *  after an error, when the IdP bounced back within 15 s (loop guard), or for social shortcuts. */
  autoRedirect?: boolean;
}) {
  const a = useAuth();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const err = authErrorMessage(new URLSearchParams(window.location.search).get("auth_error"));
    setError(err);
    if (!autoRedirect || err) return;
    const KEY = "pc_auth_auto_redirect_at";
    let last = 0;
    try {
      last = Number(window.sessionStorage.getItem(KEY) ?? 0);
      window.sessionStorage.setItem(KEY, String(Date.now()));
    } catch {
      /* storage blocked: still redirect once */
    }
    if (Date.now() - last < 15_000) return; // bounced straight back: show the button instead of looping
    setBusy("primary");
    if (mode === "sign-up") a.signUp({ returnTo });
    else a.signIn({ returnTo, loginHint });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const go = (key: string, idpHint?: string) => {
    setBusy(key);
    if (mode === "sign-up") a.signUp({ returnTo, idpHint });
    else a.signIn({ returnTo, idpHint, loginHint });
  };
  const idps = enabledIdps();
  return (
    <div className="flex flex-col gap-3" data-testid="keycloak-sign-in">
      {error ? (
        <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <button
        type="button"
        data-testid="auth-primary"
        className={`${btn} bg-secondary text-white hover:bg-[#1d4ed8]`}
        disabled={busy != null}
        onClick={() => go("primary")}
      >
        {busy === "primary"
          ? "Opening secure sign-in…"
          : (primaryLabel ?? (mode === "sign-up" ? "Create account" : "Sign in"))}
      </button>
      {idps.includes("google") ? (
        <button
          type="button"
          data-testid="auth-google"
          className={`${btn} border border-primary/15 bg-white text-primary hover:bg-primary/5`}
          disabled={busy != null}
          onClick={() => go("google", "google")}
        >
          Continue with Google
        </button>
      ) : null}
      {idps.includes("apple") ? (
        <button
          type="button"
          data-testid="auth-apple"
          className={`${btn} bg-black text-white hover:opacity-90`}
          disabled={busy != null}
          onClick={() => go("apple", "apple")}
        >
          Continue with Apple
        </button>
      ) : null}
    </div>
  );
}
