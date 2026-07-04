"use client";

import { useEffect, useState, type ReactNode } from "react";
import { SignOutButton, useAuth } from "@clerk/nextjs";
import { LogOut, ShieldAlert } from "lucide-react";
import { useRouter } from "@/i18n/navigation";
import { fetchCustomerAccess } from "@/lib/customer-access";
import { isClerkConfigured } from "@/lib/env";

export default function CustomerAccessGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const [checking, setChecking] = useState(isClerkConfigured());
  const [denied, setDenied] = useState(false);
  const [denyReason, setDenyReason] = useState("");

  useEffect(() => {
    if (!isClerkConfigured()) {
      setChecking(false);
      return;
    }
    if (!isLoaded) return;
    if (!isSignedIn) {
      router.replace("/login");
      return;
    }

    let cancelled = false;
    void (async () => {
      setChecking(true);
      try {
        const token = await getToken();
        if (!token) throw new Error("missing_token");
        await fetchCustomerAccess(token);
        if (!cancelled) setChecking(false);
      } catch (err) {
        if (cancelled) return;
        setDenied(true);
        setDenyReason(err instanceof Error ? err.message : "customer_access_denied");
        setChecking(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn, getToken, router]);

  if (!isClerkConfigured()) {
    return <>{children}</>;
  }

  if (!isLoaded || checking) {
    return <p className="type-small text-muted py-16 text-center">Verifying customer access…</p>;
  }

  if (denied) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center px-4">
        <div className="max-w-md rounded-2xl border border-amber-200 bg-white p-8 text-center shadow-sm">
          <ShieldAlert className="mx-auto h-10 w-10 text-amber-600" />
          <h2 className="mt-4 text-lg font-bold text-primary">Customer access unavailable</h2>
          <p className="mt-2 text-sm text-muted">
            {denyReason === "email_required"
              ? "Add a verified email to your account to view orders."
              : "We could not verify your customer account."}
          </p>
          <SignOutButton redirectUrl="/login">
            <button
              type="button"
              className="mt-6 inline-flex items-center gap-2 rounded-xl border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </SignOutButton>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
