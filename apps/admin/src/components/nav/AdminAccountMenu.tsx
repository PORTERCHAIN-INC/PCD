"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronDown, KeyRound, LogIn, LogOut, Settings, Shield, User } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { initials } from "@/lib/crmFormat";
import { publicEnv } from "@/lib/env";
import HeaderDropdown from "@/components/nav/HeaderDropdown";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { clearStaffSession } from "@/lib/staff-session";
import { createPasskey, credentialToJson, passkeysSupported } from "@/lib/staff-webauthn";
import { adminFetch } from "@/lib/api";
import { notifyStaffPasskeyChanged } from "@/lib/staff-security";
import { useOptionalSessionContext } from "@porterchain/auth";

/** Display labels for admin_users.role — never show a generic "Staff" for admins. */
const ROLE_LABELS: Record<string, string> = {
  super_admin: "Super Admin",
  admin: "Admin",
  operations_manager: "Operations Manager",
  dispatcher: "Dispatcher",
  support: "Support",
  support_lead: "Support Lead",
  sales: "Sales",
  sales_manager: "Sales Manager",
  finance: "Finance",
  compliance: "Compliance",
  developer: "Developer",
  marketing: "Marketing",
  read_only: "Read Only",
  fleet_manager: "Fleet Manager",
};

const ADMIN_ROLE_PRIORITY = [
  "super_admin",
  "admin",
  "operations_manager",
  "dispatcher",
  "support_lead",
  "support",
  "sales_manager",
  "sales",
  "finance",
  "fleet_manager",
  "compliance",
  "developer",
  "marketing",
  "read_only",
] as const;

function roleLabel(role: string) {
  const key = role.trim().toLowerCase();
  if (ROLE_LABELS[key]) return ROLE_LABELS[key];
  return role.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function resolveAdminRole(
  profileRole: string | null | undefined,
  sessionRoles: string[] | undefined
): string {
  if (profileRole && profileRole.toLowerCase() !== "staff") {
    return profileRole;
  }
  const roles = (sessionRoles || []).map((r) => r.toLowerCase());
  for (const preferred of ADMIN_ROLE_PRIORITY) {
    if (roles.includes(preferred)) return preferred;
  }
  return "admin";
}

export default function AdminAccountMenu() {
  const router = useRouter();
  const { profile } = useAdminProfile();
  const { getApiToken, isSignedIn } = useAdminAuth();
  const session = useOptionalSessionContext()?.session;
  const [passkeyMsg, setPasskeyMsg] = useState<string | null>(null);
  const [passkeyBusy, setPasskeyBusy] = useState(false);

  if (!isSignedIn && !profile && !session) {
    return (
      <Link
        href="/sign-in"
        className="flex h-10 items-center gap-2 rounded-full border border-primary/10 bg-white pl-3 pr-3 text-sm font-medium text-primary shadow-sm hover:bg-gray-bg"
      >
        <LogIn className="h-4 w-4 text-secondary" />
        Sign in
      </Link>
    );
  }

  const email = profile?.email ?? session?.email ?? "";
  const name = profile?.name ?? email.split("@")[0] ?? "Admin";
  const role = resolveAdminRole(profile?.role, session?.roles);
  const label = roleLabel(role);

  async function registerPasskey() {
    setPasskeyBusy(true);
    setPasskeyMsg(null);
    try {
      const token = await getApiToken();
      const options = await adminFetch<Record<string, unknown> & { challenge_id?: string }>(
        "/v1/auth/staff/passkey/register/options",
        token,
        { method: "POST" }
      );
      const challengeId = String(options.challenge_id || "");
      const cred = await createPasskey(options);
      await adminFetch("/v1/auth/staff/passkey/register/verify", token, {
        method: "POST",
        body: JSON.stringify({
          challenge_id: challengeId,
          credential: credentialToJson(cred),
          device_label: "This device",
        }),
      });
      notifyStaffPasskeyChanged();
      setPasskeyMsg("Passkey saved — use it on sign-in.");
    } catch (e) {
      setPasskeyMsg(e instanceof Error ? e.message : "passkey_failed");
    } finally {
      setPasskeyBusy(false);
    }
  }

  return (
    <HeaderDropdown
      align="right"
      width="md"
      trigger={({ open, triggerProps }) => (
        <button
          type="button"
          {...triggerProps}
          aria-label="Account menu"
          className={cn(
            "flex h-10 max-w-[12rem] items-center gap-2 rounded-full border border-primary/10 bg-white py-1 pl-1 pr-2.5 shadow-sm transition hover:bg-gray-bg",
            open && "border-secondary/30 ring-2 ring-secondary/20"
          )}
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary/10 text-xs font-bold text-secondary">
            {initials(name || email)}
          </span>
          <span className="hidden min-w-0 flex-1 truncate text-left text-sm font-medium text-primary sm:block">
            {name}
          </span>
          <ChevronDown className="h-4 w-4 shrink-0 text-muted" />
        </button>
      )}
    >
      <div className="border-b border-primary/8 px-4 py-3">
        <p className="truncate text-sm font-semibold text-primary">{name}</p>
        <p className="truncate text-xs text-muted">{email}</p>
        <p className="mt-1 inline-flex items-center gap-1 rounded-full bg-secondary/10 px-2 py-0.5 text-[11px] font-semibold text-secondary">
          <Shield className="h-3 w-3" />
          {label}
        </p>
        <p className="mt-1 text-[10px] font-medium uppercase tracking-wide text-muted">Staff IdP</p>
      </div>

      <div className="p-2">
        <AccountMenuLink
          href="/account/security"
          icon={Shield}
          label="Security"
          hint="Sessions & passkeys"
        />
        <AccountMenuLink
          href="/settings?section=users"
          icon={User}
          label="Users"
          hint="Staff directory"
        />
        <AccountMenuLink
          href="/settings"
          icon={Settings}
          label="Admin settings"
          hint="Integrations & RBAC"
        />
        {passkeysSupported() && (
          <button
            type="button"
            disabled={passkeyBusy}
            onClick={() => void registerPasskey()}
            className="flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-sm transition hover:bg-gray-bg disabled:opacity-50"
          >
            <KeyRound className="mt-0.5 h-4 w-4 shrink-0 text-secondary" />
            <span className="min-w-0 text-left">
              <span className="block font-medium text-primary">
                {passkeyBusy ? "Registering…" : "Add passkey"}
              </span>
              <span className="block text-xs text-muted">Passwordless sign-in on this device</span>
            </span>
          </button>
        )}
        {passkeyMsg && <p className="px-3 pb-2 text-xs text-muted">{passkeyMsg}</p>}
      </div>

      <div className="border-t border-primary/8 bg-slate-50/80 p-2">
        <button
          type="button"
          onClick={() => {
            void clearStaffSession(publicEnv.porterchainApiUrl).then(() =>
              router.replace("/sign-in")
            );
          }}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-red-200 bg-white px-4 py-2.5 text-sm font-semibold text-red-600 shadow-sm transition hover:bg-red-50"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </HeaderDropdown>
  );
}

function AccountMenuLink({
  href,
  icon: Icon,
  label,
  hint,
}: {
  href: string;
  icon: typeof User;
  label: string;
  hint: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-start gap-3 rounded-xl px-3 py-2.5 text-sm transition hover:bg-gray-bg"
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-secondary" />
      <span className="min-w-0">
        <span className="block font-medium text-primary">{label}</span>
        <span className="block text-xs text-muted">{hint}</span>
      </span>
    </Link>
  );
}
