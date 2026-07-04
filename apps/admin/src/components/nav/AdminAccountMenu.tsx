"use client";

import Link from "next/link";
import { SignInButton, SignOutButton, useUser } from "@clerk/nextjs";
import { ChevronDown, LogIn, LogOut, Settings, Shield, User } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { initials } from "@/lib/crmFormat";
import { isClerkConfigured } from "@/lib/env";
import HeaderDropdown from "@/components/nav/HeaderDropdown";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";

function roleLabel(role: string) {
  return role.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function AdminAccountMenu() {
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
  const { profile } = useAdminProfile();

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

  const email = profile?.email ?? user.primaryEmailAddress?.emailAddress ?? "";
  const name = profile?.name ?? user.fullName ?? user.username ?? "Admin";
  const avatar = user.imageUrl;
  const role = profile?.role ?? "staff";

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
            <span className="block truncate text-[10px] text-muted">{roleLabel(role)}</span>
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
            <span className="mt-1.5 inline-block rounded-full bg-secondary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-secondary">
              {roleLabel(role)}
            </span>
          </div>
        </div>
      </div>

      <div className="p-1.5">
        <AccountMenuLink
          href="/settings"
          icon={User}
          label="Profile"
          hint="View your staff profile"
        />
        <AccountMenuLink
          href="/settings"
          icon={Shield}
          label="Account & security"
          hint="Clerk session settings"
        />
        <AccountMenuLink
          href="/settings"
          icon={Settings}
          label="Admin settings"
          hint="Integrations & RBAC"
        />
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
