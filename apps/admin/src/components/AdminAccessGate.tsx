"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { SignOutButton, useAuth } from "@clerk/nextjs";
import { LogOut, ShieldAlert } from "lucide-react";
import { Spinner } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { fetchAdminAccess, type AdminStaffProfile } from "@/lib/admin-access";
import { isClerkConfigured } from "@/lib/env";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";

type Props = {
  children: ReactNode;
  onProfile?: (profile: AdminStaffProfile) => void;
};

export default function AdminAccessGate({ children, onProfile }: Props) {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const { getApiToken } = useAdminAuth();
  const { profile, setProfile } = useAdminProfile();
  const [checking, setChecking] = useState(!profile);
  const [denied, setDenied] = useState(false);
  const [errorDetail, setErrorDetail] = useState("");

  useEffect(() => {
    if (!isClerkConfigured()) {
      setChecking(false);
      return;
    }
    if (!isLoaded) return;
    if (!isSignedIn) {
      setProfile(null);
      router.replace("/sign-in");
      return;
    }

    let cancelled = false;
    void (async () => {
      setChecking(true);
      setDenied(false);
      setErrorDetail("");
      try {
        const token = await getApiToken();
        const staff = await fetchAdminAccess(token);
        if (cancelled) return;
        setProfile(staff);
        onProfile?.(staff);
        setChecking(false);
      } catch (err) {
        if (cancelled) return;
        setProfile(null);
        setDenied(true);
        setErrorDetail(err instanceof Error ? err.message : "admin_access_denied");
        setChecking(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn, getApiToken, router, setProfile, onProfile]);

  if (!isClerkConfigured()) {
    return <>{children}</>;
  }

  if (!isLoaded || checking) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3">
        <Spinner />
        <p className="text-sm text-muted">Verifying staff access…</p>
      </div>
    );
  }

  if (denied) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center p-6">
        <div className="max-w-md rounded-2xl border border-amber-200 bg-white p-8 text-center shadow-sm">
          <ShieldAlert className="mx-auto h-12 w-12 text-amber-600" />
          <h1 className="mt-4 text-xl font-bold text-primary">Staff access required</h1>
          <p className="mt-2 text-sm text-muted">
            {errorDetail === "porterchain_api_timeout"
              ? "Porterchain API did not respond. Start the API on port 8001 (apps/api) and refresh."
              : errorDetail === "admin_user_not_found" || errorDetail === "admin_user_inactive"
                ? "Your Clerk account is not provisioned as Porterchain admin staff. Access is invite-only — contact a super admin to add your email in Admin Settings → Staff."
                : errorDetail.startsWith("identity_conflict:")
                  ? "This Clerk account is also linked to the customer portal. Staff accounts must be admin-only — sign out and use a separate email for retail bookings, or ask a super admin to remove the customer link."
                  : errorDetail
                    ? `Access check failed: ${errorDetail}`
                    : "Your Clerk account is not provisioned as Porterchain admin staff. Access is invite-only — contact a super admin to add your email in Admin Settings → Staff."}
          </p>
          {errorDetail !== "porterchain_api_timeout" && (
            <p className="mt-4 text-xs text-muted">
              Self-service sign-up does not grant admin access even if Clerk login succeeds.
            </p>
          )}
          <SignOutButton redirectUrl="/sign-in">
            <button
              type="button"
              className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-red-200 bg-white px-4 py-2.5 text-sm font-semibold text-red-600 hover:bg-red-50"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </SignOutButton>
          <button
            type="button"
            onClick={() => router.replace("/sign-in")}
            className="mt-2 w-full text-xs text-muted hover:text-secondary"
          >
            Back to sign in
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
