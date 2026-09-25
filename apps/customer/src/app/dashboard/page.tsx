"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Spinner } from "@porterchain/ui/loading";
import CustomerShell from "@/components/CustomerShell";
import CustomerWelcomeHome from "@/components/welcome/CustomerWelcomeHome";
import { customerApi } from "@/lib/api";
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
  const {
    data: dashboard,
    error,
    isLoading,
  } = useQuery({
    queryKey: ["customer-dashboard"],
    enabled: isSignedIn,
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");
      return customerApi.dashboard(token);
    },
  });

  return (
    <CustomerShell>
      {isLoading && !dashboard ? (
        <div className="flex min-h-[50vh] items-center justify-center">
          <Spinner label="Opening your home…" />
        </div>
      ) : (
        <CustomerWelcomeHome
          dashboard={dashboard ?? null}
          error={error ? "Could not refresh deliveries. You can still book capacity." : undefined}
          getToken={getToken}
        />
      )}
    </CustomerShell>
  );
}
