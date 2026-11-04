"use client";

import { useAuth, useUser } from "@porterchain/auth/oidc/client";
import type { ReactNode } from "react";
import { isAuthConfigured } from "@/lib/env";

export type PortalAuthValue = {
  ready: boolean;
  getToken: () => Promise<string | null>;
  userId: string | null;
  email: string;
  phone: string;
};

/** One place that hands pages a token: Keycloak in prod, the local `dev` bearer otherwise. */
export default function PortalAuth({
  children,
}: {
  children: (auth: PortalAuthValue) => ReactNode;
}) {
  if (!isAuthConfigured()) {
    return (
      <>
        {children({
          ready: true,
          getToken: async () => "dev",
          userId: "dev_customer_user",
          email: "",
          phone: "",
        })}
      </>
    );
  }
  return <KeycloakAuth>{children}</KeycloakAuth>;
}

function KeycloakAuth({ children }: { children: (auth: PortalAuthValue) => ReactNode }) {
  const { isLoaded, getToken, userId } = useAuth();
  const { user } = useUser();
  return (
    <>
      {children({
        ready: isLoaded,
        getToken,
        userId: userId ?? null,
        email: user?.email ?? "",
        phone: "",
      })}
    </>
  );
}
