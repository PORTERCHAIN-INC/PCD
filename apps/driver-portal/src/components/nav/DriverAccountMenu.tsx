"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { AlertTriangle, ChevronDown, FileText, LogIn, LogOut, Truck, User } from "lucide-react";
import { driverApi, driverLogout, hasDriverSession } from "@/lib/api";
import { isClerkConfigured } from "@/lib/env";
import { cn, initials } from "@/lib/utils";
import HeaderDropdown from "@/components/nav/HeaderDropdown";
import { useDriverProfile } from "@/components/nav/DriverProfileContext";

function statusLabel(status: string): string {
  const s = status.toLowerCase();
  if (s === "approved") return "Approved";
  if (s === "pending") return "Pending review";
  if (s === "suspended") return "Suspended";
  return status;
}

export default function DriverAccountMenu() {
  const router = useRouter();
  const { profile, setProfile } = useDriverProfile();
  const { user, isLoaded: clerkLoaded } = useUser();
  const [authed, setAuthed] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const ok = await hasDriverSession();
      if (cancelled) return;
      setAuthed(ok);
      if (ok) {
        try {
          const me = await driverApi.me();
          if (!cancelled) setProfile(me);
        } catch {
          if (!cancelled) setProfile(null);
        }
      }
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [setProfile]);

  if (loading) {
    return <div className="h-10 w-10 animate-pulse rounded-full bg-primary/10" />;
  }

  if (!authed) {
    return (
      <Link
        href="/login"
        className="flex h-10 items-center gap-2 rounded-full bg-secondary pl-4 pr-4 text-sm font-semibold text-white shadow-sm hover:bg-secondary/90"
      >
        <LogIn className="h-4 w-4" />
        Sign in
      </Link>
    );
  }

  const name = profile?.full_name ?? user?.fullName ?? "Driver";
  const email = profile?.email ?? user?.primaryEmailAddress?.emailAddress ?? "";
  const avatar = isClerkConfigured() && clerkLoaded ? user?.imageUrl : undefined;
  const status = profile?.status ?? "pending";
  const availability = profile?.availability ?? "offline";
  const isOnline = profile?.is_online ?? false;

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
            <span className="block truncate text-[10px] text-muted">
              {isOnline ? "Online" : availability.replace(/_/g, " ")}
            </span>
          </span>
          <ChevronDown
            className={cn("hidden h-3.5 w-3.5 shrink-0 text-muted sm:block", open && "rotate-180")}
          />
        </button>
      )}
    >
      <ProfileHeader
        name={name}
        email={email}
        avatar={avatar}
        status={status}
        isOnline={isOnline}
      />

      <div className="p-1.5">
        <AccountMenuLink
          href="/profile"
          icon={User}
          label="Driver profile"
          hint="License, vehicle, compliance"
        />
        <AccountMenuLink
          href="/profile#documents"
          icon={FileText}
          label="Documents"
          hint="Uploads and expiry"
        />
        <AccountMenuLink
          href="/shift"
          icon={Truck}
          label="Shift & availability"
          hint="Online status and route"
        />
        <AccountMenuLink
          href="/emergency"
          icon={AlertTriangle}
          label="Emergency SOS"
          hint="Critical alert to operations"
          danger
        />
      </div>

      <div className="border-t border-primary/8 bg-slate-50/80 p-2">
        <button
          type="button"
          onClick={async () => {
            await driverLogout();
            setProfile(null);
            router.push("/login");
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

function ProfileHeader({
  name,
  email,
  avatar,
  status,
  isOnline,
}: {
  name: string;
  email: string;
  avatar?: string;
  status: string;
  isOnline: boolean;
}) {
  return (
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
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            <span className="inline-block rounded-full bg-secondary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-secondary">
              {statusLabel(status)}
            </span>
            <span
              className={cn(
                "inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                isOnline ? "bg-emerald-100 text-emerald-800" : "bg-gray-100 text-gray-600"
              )}
            >
              {isOnline ? "Online" : "Offline"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function AccountMenuLink({
  href,
  icon: Icon,
  label,
  hint,
  danger,
}: {
  href: string;
  icon: typeof User;
  label: string;
  hint: string;
  danger?: boolean;
}) {
  return (
    <Link
      href={href}
      role="menuitem"
      className={cn(
        "flex items-start gap-3 rounded-lg px-3 py-2.5 transition hover:bg-gray-bg",
        danger && "hover:bg-red-50"
      )}
    >
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", danger ? "text-red-600" : "text-muted")} />
      <span className="min-w-0">
        <span className={cn("block text-sm font-medium", danger ? "text-red-700" : "text-primary")}>
          {label}
        </span>
        <span className="block text-xs text-muted">{hint}</span>
      </span>
    </Link>
  );
}
