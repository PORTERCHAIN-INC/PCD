"use client";

import { ExternalLink, KeyRound, LogOut, ShieldCheck } from "lucide-react";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { clearStaffSession } from "@/lib/staff-session";
import { stepUpUrl } from "@/lib/staff-step-up";

/**
 * Staff sign-in security lives in Keycloak (`pc-admin`): password, authenticator app (TOTP,
 * required for admin tiers), passkeys and active sessions are managed in the account console.
 */
export default function AccountSecurityClient() {
  const { profile } = useAdminProfile();
  const card = "flex items-start gap-3 rounded-2xl border border-primary/10 bg-white p-5 shadow-sm";
  const btn =
    "inline-flex items-center gap-2 rounded-xl border border-primary/15 px-4 py-2 text-sm font-semibold text-primary hover:bg-primary/5";
  return (
    <div className="mx-auto max-w-2xl space-y-4 p-6" data-testid="account-security">
      <h1 className="text-2xl font-bold text-primary">Security</h1>
      <p className="text-sm text-muted">
        Signed in as {profile?.email ?? "staff"} through Keycloak. Sensitive actions ask you to sign
        in again if your last sign-in was more than 15 minutes ago.
      </p>
      <section className={card}>
        <ShieldCheck className="mt-0.5 h-5 w-5 text-secondary" />
        <div className="space-y-3">
          <p className="text-sm">
            Change your password, set up or replace your authenticator app, add a passkey and review
            signed-in devices in your Keycloak account.
          </p>
          <a href="/auth/account" className={btn} target="_blank" rel="noreferrer">
            <ExternalLink className="h-4 w-4" />
            Open account console
          </a>
        </div>
      </section>
      <section className={card}>
        <KeyRound className="mt-0.5 h-5 w-5 text-secondary" />
        <div className="space-y-3">
          <p className="text-sm">
            Confirm it&apos;s you now to unlock sensitive actions for 15 minutes.
          </p>
          <a href={stepUpUrl("/account/security")} className={btn}>
            Re-authenticate
          </a>
        </div>
      </section>
      <button type="button" className={btn} onClick={() => void clearStaffSession()}>
        <LogOut className="h-4 w-4" />
        Sign out
      </button>
    </div>
  );
}
