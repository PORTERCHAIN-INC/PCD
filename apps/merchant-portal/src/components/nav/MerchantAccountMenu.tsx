"use client";

import Link from "next/link";
import { SignInButton, SignOutButton, useClerk, useUser } from "@clerk/nextjs";
import { Building2, ChevronDown, Key, LogIn, LogOut, Settings, User, Users } from "lucide-react";
import { cn, initials } from "@/lib/utils";
import { isClerkConfigured, useLocalDevAuth } from "@/lib/env";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import HeaderDropdown from "@/components/nav/HeaderDropdown";
import MerchantCompanySwitcher from "@/components/nav/MerchantCompanySwitcher";
import { useMerchantProfile } from "@/components/nav/MerchantProfileContext";
import { merchantStatusLabel } from "@/lib/catalog";
import { merchantRoleLabel } from "@/lib/team";

function LocalDevAccountMenu() {
  const { session } = useMerchantAuth();
  const email = session?.user_email || "admin@porterchain.com";
  const name = session?.company_name || "Dev Merchant Co.";

  return (
    <div className="flex h-10 items-center gap-2 rounded-full border border-primary/10 bg-white pl-1 pr-3 text-sm font-medium text-primary shadow-sm">
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary/10 text-xs font-semibold text-secondary">
        {initials(name)}
      </span>
      <span className="hidden max-w-[10rem] truncate sm:inline">{email}</span>
    </div>
  );
}

export default function MerchantAccountMenu() {
  if (useLocalDevAuth()) {
    return <LocalDevAccountMenu />;
  }
  if (!isClerkConfigured()) {
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
          {avatar ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={avatar}
              alt=""
              className="h-8 w-8 rounded-full object-cover ring-2 ring-white"
            />
          ) : (
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-xs font-bold text-white">
              {initials(name)}
            </span>
          )}
          <span className="hidden min-w-0 flex-1 text-left sm:block">
            <span className="block truncate text-xs font-semibold text-primary">
              {name.split(" ")[0]}
            </span>
            <span className="block truncate text-[10px] text-muted">{company}</span>
          </span>
          <ChevronDown
            className={cn("h-4 w-4 shrink-0 text-muted transition", open && "rotate-180")}
          />
        </button>
      )}
    >
      <div className="border-b border-primary/8 bg-gradient-to-br from-slate-50 to-white px-4 py-4">
        <div className="flex items-center gap-3">
          {avatar ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={avatar}
              alt=""
              className="h-12 w-12 rounded-full object-cover ring-2 ring-white shadow-md"
            />
          ) : (
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary text-sm font-bold text-white shadow-md">
              {initials(name)}
            </span>
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-primary">{name}</p>
            <p className="truncate text-xs text-muted">{email}</p>
            <span className="mt-1.5 inline-block rounded-full bg-secondary/10 px-2 py-0.5 text-[10px] font-semibold tracking-wide text-secondary">
              {statusLabel}
            </span>
            {roleLabel ? (
              <span className="ml-1.5 inline-block rounded-full bg-primary/5 px-2 py-0.5 text-[10px] font-semibold text-primary">
                {roleLabel}
              </span>
            ) : null}
          </div>
        </div>
        <p className="mt-3 flex items-center gap-1.5 truncate text-xs text-muted">
          <Building2 className="h-3.5 w-3.5 shrink-0" />
          {company}
        </p>
        <div className="mt-3">
          <MerchantCompanySwitcher />
        </div>
      </div>

      <div className="p-1.5">
        <button
          type="button"
          onClick={() => openUserProfile()}
          className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition hover:bg-gray-bg"
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-secondary/10">
            <User className="h-4 w-4 text-secondary" />
          </span>
          <span className="min-w-0">
            <span className="block text-sm font-medium text-primary">My account</span>
            <span className="block text-xs text-muted">Password, MFA, email</span>
          </span>
        </button>
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
          <AccountMenuLink
            href="/api"
            icon={Key}
            label="Integrations"
            hint="API keys and webhooks"
          />
        ) : null}
      </div>

      <div className="border-t border-primary/8 bg-slate-50/80 p-2">
        <SignOutButton redirectUrl="/sign-in">
          <button
            type="button"
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-red-200 bg-white px-4 py-2.5 text-sm font-semibold text-red-600 shadow-sm transition hover:bg-red-50"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </SignOutButton>
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
      className="flex items-center gap-3 rounded-xl px-3 py-2.5 transition hover:bg-gray-bg"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-secondary/10">
        <Icon className="h-4 w-4 text-secondary" />
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-medium text-primary">{label}</span>
        <span className="block text-xs text-muted">{hint}</span>
      </span>
    </Link>
  );
}
