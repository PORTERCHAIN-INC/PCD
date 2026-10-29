"use client";

import { useEffect, useState } from "react";
import { KeyRound, Settings, Shield, User } from "lucide-react";
import {
  AccountBadge,
  AccountMenu,
  AccountMenuLink,
  AccountSignInLink,
  AccountSignOutButton,
} from "@porterchain/ui/account-menu";
import { publicEnv } from "@/lib/env";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { clearStaffSession } from "@/lib/staff-session";
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
  const { profile } = useAdminProfile();
  const { isSignedIn } = useAdminAuth();
  const session = useOptionalSessionContext()?.session;
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
        <p className="mt-1 text-[10px] font-medium uppercase tracking-wide text-muted">
          Keycloak · MFA
        </p>
      }
      footer={
        <AccountSignOutButton
          onClick={() => {
            void clearStaffSession(publicEnv.porterchainApiUrl);
          }}
        />
      }
    >
      <AccountMenuLink
        href="/account/security"
        icon={Shield}
        label="Security"
        hint="Password, authenticator & sessions"
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
      <AccountMenuLink
        href="/auth/account"
        icon={KeyRound}
        label="Keycloak account"
        hint="Manage sign-in methods"
      />
    </AccountMenu>
  );
}
