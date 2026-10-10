"use client";

import { useAuth, useUser } from "@clerk/nextjs";
import type { ReactNode } from "react";
import { isClerkConfigured } from "@/lib/env";

export type PortalAuthValue = {
  ready: boolean;
  getToken: () => Promise<string | null>;
  userId: string | null;
  email: string;
  phone: string;
};

/** One place that hands pages a token: Clerk in prod, the local `dev` bearer otherwise. */
export default function PortalAuth({
  children,
}: {
  children: (auth: PortalAuthValue) => ReactNode;
}) {
  if (!isClerkConfigured()) {
    return (
      <>
        {children({
          ready: true,
          getToken: async () => "dev",
          userId: "dev_clerk_user",
          email: "",
          phone: "",
        })}
      </>
    );
  }
  return <ClerkAuth>{children}</ClerkAuth>;
}

function ClerkAuth({ children }: { children: (auth: PortalAuthValue) => ReactNode }) {
  const { isLoaded, getToken, userId } = useAuth();
  const { user } = useUser();
  return (
    <>
      {children({
        ready: isLoaded,
        getToken,
        userId: userId ?? null,
        email: user?.primaryEmailAddress?.emailAddress ?? "",
        phone: user?.primaryPhoneNumber?.phoneNumber ?? "",
      })}
    </>
  );
}
