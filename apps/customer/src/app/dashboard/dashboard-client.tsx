"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { PageSkeleton } from "@porterchain/ui/loading";
import CustomerWelcomeHome from "@/components/welcome/CustomerWelcomeHome";
import { customerApi } from "@/lib/api";
import { isClerkConfigured } from "@/lib/env";

export default function CustomerDashboardClient() {
  if (!isClerkConfigured()) {
    return <DashboardBody ready signedIn getToken={async () => "dev"} />;
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

  return <DashboardBody ready={isLoaded} signedIn={Boolean(isSignedIn)} getToken={getToken} />;
}

function DashboardBody({
  ready,
  signedIn,
  getToken,
}: {
  ready: boolean;
  signedIn: boolean;
  getToken: () => Promise<string | null>;
}) {
  const {
    data: dashboard,
    error,
    isLoading,
  } = useQuery({
    queryKey: ["customer-dashboard"],
    enabled: ready && signedIn,
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");
      return customerApi.dashboard(token);
    },
  });

  if (!dashboard && (!ready || isLoading)) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <p className="sr-only" role="status">
          Opening your home
        </p>
        <PageSkeleton rows={5} />
      </div>
    );
  }

  return (
    <CustomerWelcomeHome
      dashboard={dashboard ?? null}
      error={error ? "Could not refresh deliveries. You can still book capacity." : undefined}
      getToken={getToken}
    />
  );
}
