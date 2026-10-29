"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useUser } from "@porterchain/auth/oidc/client";
import { AlertTriangle, FileText, Truck, User } from "lucide-react";
import {
  AccountBadge,
  AccountMenu,
  AccountMenuLink,
  AccountSignInLink,
  AccountSignOutButton,
} from "@porterchain/ui/account-menu";
import { driverApi, driverLogout, hasDriverSession } from "@/lib/api";
import { isAuthConfigured } from "@/lib/env";
import { useDriverProfile } from "@/components/nav/DriverProfileContext";

function statusLabel(status: string): string {
  const s = status.toLowerCase();
  if (s === "approved") return "Approved";
  if (s === "pending") return "Pending review";
  if (s === "suspended") return "Suspended";
  return status;
}

export default function DriverAccountMenu() {
  if (isAuthConfigured()) {
    return <DriverAccountMenuWithAuth />;
  }
  return <DriverAccountMenuBody clerkUser={null} clerkLoaded={false} />;
}

function DriverAccountMenuWithAuth() {
  const { user, isLoaded: clerkLoaded } = useUser();
  return <DriverAccountMenuBody clerkUser={user} clerkLoaded={clerkLoaded} />;
}

function DriverAccountMenuBody({
  clerkUser: user,
  clerkLoaded,
}: {
  clerkUser: ReturnType<typeof useUser>["user"];
  clerkLoaded: boolean;
}) {
  const router = useRouter();
  const { profile, setProfile } = useDriverProfile();
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
    return <AccountSignInLink href="/login" primary />;
  }

  const name = profile?.full_name ?? user?.fullName ?? "Driver";
  const email = profile?.email ?? user?.email ?? "";
  const avatar = undefined;
  const status = profile?.status ?? "pending";
  const availability = profile?.availability ?? "offline";
  const isOnline = profile?.is_online ?? false;

  return (
    <AccountMenu
      name={name}
      email={email}
      avatar={avatar}
      triggerSubtitle={isOnline ? "Online" : availability.replace(/_/g, " ")}
      badges={
        <>
          <AccountBadge>{statusLabel(status).toUpperCase()}</AccountBadge>
          <AccountBadge tone={isOnline ? "success" : "neutral"}>
            {isOnline ? "ONLINE" : "OFFLINE"}
          </AccountBadge>
        </>
      }
      footer={
        <AccountSignOutButton
          onClick={async () => {
            await driverLogout();
            setProfile(null);
            router.push("/login");
          }}
        />
      }
    >
      <AccountMenuLink
        href="/account"
        icon={User}
        label="Account"
        hint="Profile, password, devices, privacy"
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
    </AccountMenu>
  );
}
