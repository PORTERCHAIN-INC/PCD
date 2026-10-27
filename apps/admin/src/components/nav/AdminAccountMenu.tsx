"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { KeyRound, Settings, Shield, User } from "lucide-react";
import {
  AccountBadge,
  AccountMenu,
  AccountMenuButton,
  AccountMenuLink,
  AccountSignInLink,
  AccountSignOutButton,
} from "@porterchain/ui/account-menu";
import { publicEnv } from "@/lib/env";
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
  // Session lives in the browser (HttpOnly cookie → client provider), so the server always
  // renders signed-out. Render a neutral avatar slot until mounted to keep hydration identical.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <span
        aria-hidden
        className="flex h-10 w-[4.5rem] items-center rounded-full border border-primary/10 bg-white"
      />
    );
  }

  if (!isSignedIn && !profile && !session) {
    return <AccountSignInLink href="/sign-in" />;
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
    <AccountMenu
      name={name}
      email={email}
      softAvatar
      richHeader={false}
      badges={
        <AccountBadge>
          <Shield className="h-3 w-3" />
          {label}
        </AccountBadge>
      }
      headerExtra={
        <p className="mt-1 text-[10px] font-medium uppercase tracking-wide text-muted">Staff IdP</p>
      }
      footer={
        <AccountSignOutButton
          onClick={() => {
            void clearStaffSession(publicEnv.porterchainApiUrl).then(() =>
              router.replace("/sign-in")
            );
          }}
        />
      }
    >
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
        <AccountMenuButton
          disabled={passkeyBusy}
          onClick={() => void registerPasskey()}
          icon={KeyRound}
          label={passkeyBusy ? "Registering…" : "Add passkey"}
          hint="Passwordless sign-in on this device"
        />
      )}
      {passkeyMsg && <p className="px-3 pb-2 text-xs text-muted">{passkeyMsg}</p>}
    </AccountMenu>
  );
}
