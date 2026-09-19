"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Spinner } from "@porterchain/ui/loading";
import CustomerShell from "@/components/CustomerShell";
import CustomerWelcomeHome from "@/components/welcome/CustomerWelcomeHome";
import { customerApi, type CustomerDashboard } from "@/lib/api";
import { isClerkConfigured } from "@/lib/env";

export default function DashboardPage() {
  if (!isClerkConfigured()) {
    return <DashboardBody isSignedIn getToken={async () => "dev"} />;
  }
  return <DashboardWithClerk />;
}

function DashboardWithClerk() {
  const router = useRouter();
  const { isSignedIn, isLoaded, getToken } = useAuth();

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.replace("/sign-in?redirect_url=/dashboard");
    }
  }, [isLoaded, isSignedIn, router]);

  if (!isLoaded || !isSignedIn) {
    return (
      <main className="flex min-h-dvh items-center justify-center bg-gray-bg">
        <Spinner label="Loading your account…" />
      </main>
    );
  }

  return <DashboardBody isSignedIn={isSignedIn} getToken={getToken} />;
}

function DashboardBody({
  isSignedIn,
  getToken,
}: {
  isSignedIn: boolean;
  getToken: () => Promise<string | null>;
}) {
  const [dashboard, setDashboard] = useState<CustomerDashboard | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isSignedIn) return;
    let cancelled = false;
    void (async () => {
      try {
        const token = await getToken();
        if (!token || cancelled) return;
        const data = await customerApi.dashboard(token);
        if (!cancelled) {
          setDashboard(data);
          setError("");
        }
      } catch {
        if (!cancelled) setError("Could not refresh deliveries. You can still book capacity.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isSignedIn, getToken]);

  return (
    <CustomerShell>
      {loading && !dashboard ? (
        <div className="flex min-h-[50vh] items-center justify-center">
          <Spinner label="Opening your home…" />
        </div>
      ) : (
        <CustomerWelcomeHome dashboard={dashboard} error={error || undefined} getToken={getToken} />
      )}
    </CustomerShell>
  );
}
