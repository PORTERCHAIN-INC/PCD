"use client";

import { SignInButton, SignOutButton, useClerk, useUser } from "@clerk/nextjs";
import { Building2, Key, LogIn, Settings, User, Users } from "lucide-react";
import {
  AccountAvatar,
  AccountBadge,
  AccountMenu,
  AccountMenuButton,
  AccountMenuLink,
  AccountSignInLink,
  AccountSignOutButton,
} from "@porterchain/ui/account-menu";
import { isClerkConfigured, useLocalDevAuth } from "@/lib/env";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import MerchantCompanySwitcher from "@/components/nav/MerchantCompanySwitcher";
import { useMerchantProfile } from "@/components/nav/MerchantProfileContext";
import { merchantStatusLabel } from "@/lib/catalog";
import { merchantRoleLabel } from "@/lib/team";

function LocalDevAccountMenu() {
  const { session } = useMerchantAuth();
  const email = session?.user_email || "merchant@porterchain.com";
  const name = session?.company_name || "Dev Merchant Co.";

  return (
    <div className="flex h-10 items-center gap-2 rounded-full border border-primary/10 bg-white pl-1 pr-3 text-sm font-medium text-primary shadow-sm">
      <AccountAvatar name={name} soft />
      <span className="hidden max-w-[10rem] truncate sm:inline">{email}</span>
    </div>
  );
}

export default function MerchantAccountMenu() {
  if (useLocalDevAuth()) {
    return <LocalDevAccountMenu />;
  }
  if (!isClerkConfigured()) {
    return <AccountSignInLink href="/sign-in" />;
  }

  return <ClerkAccountMenu />;
}

function ClerkAccountMenu() {
  const { isLoaded, isSignedIn, user } = useUser();
  const { openUserProfile } = useClerk();
  const { profile } = useMerchantProfile();
  const { session, role, modules } = useMerchantAuth();

  if (!isLoaded) {
    return <div className="h-10 w-10 animate-pulse rounded-full bg-primary/10" />;
  }

  if (!isSignedIn) {
    return (
      <SignInButton mode="redirect">
        <button
          type="button"
          className="flex h-10 items-center gap-2 rounded-full bg-secondary pl-4 pr-4 text-sm font-semibold text-white shadow-sm hover:bg-secondary/90"
        >
          <LogIn className="h-4 w-4" />
          Sign in
        </button>
      </SignInButton>
    );
  }

  const email =
    profile?.email ?? session?.user_email ?? user.primaryEmailAddress?.emailAddress ?? "";
  const name =
    user.fullName ?? user.username ?? session?.company_name ?? profile?.company_name ?? "Merchant";
  const avatar = user.imageUrl;
  const company = session?.company_name ?? profile?.company_name ?? "Merchant account";
  const status = session?.status ?? profile?.status ?? "ACTIVE";
  const statusLabel = session?.status_label || merchantStatusLabel(status);
  const roleLabel = session?.role_label || merchantRoleLabel(role || session?.role);

  return (
    <AccountMenu
      name={name}
      email={email}
      avatar={avatar}
      triggerSubtitle={company}
      badges={
        <>
          <AccountBadge>{statusLabel}</AccountBadge>
          {roleLabel ? <AccountBadge tone="neutral">{roleLabel}</AccountBadge> : null}
        </>
      }
      headerExtra={
        <>
          <p className="mt-3 flex items-center gap-1.5 truncate text-xs text-muted">
            <Building2 className="h-3.5 w-3.5 shrink-0" />
            {company}
          </p>
          <div className="mt-3">
            <MerchantCompanySwitcher />
          </div>
        </>
      }
      footer={
        <SignOutButton redirectUrl="/sign-in">
          <AccountSignOutButton />
        </SignOutButton>
      }
    >
      <AccountMenuButton
        onClick={() => openUserProfile()}
        icon={User}
        label="My account"
        hint="Password, MFA, email"
      />
      {modules.includes("settings") ? (
        <AccountMenuLink
          href="/settings"
          icon={Settings}
          label="Company settings"
          hint="Profile, locations, tax"
        />
      ) : null}
      {modules.includes("users") ? (
        <AccountMenuLink href="/team" icon={Users} label="Team" hint="Members, roles, seats" />
      ) : null}
      {modules.includes("api_keys") ? (
        <AccountMenuLink href="/api" icon={Key} label="Integrations" hint="API keys and webhooks" />
      ) : null}
    </AccountMenu>
  );
}
