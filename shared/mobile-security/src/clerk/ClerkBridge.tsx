"use client";

import { createElement, type ReactNode } from "react";
import { isClerkConfigured, type MobileSecurityEnv } from "../config";

type ClerkBridgeProps = {
  children: ReactNode;
  env: MobileSecurityEnv;
};

export function ClerkBridge({ children, env }: ClerkBridgeProps) {
  if (!isClerkConfigured(env)) {
    return <>{children}</>;
  }

  try {
    const { ClerkProvider } = require("@clerk/clerk-expo") as {
      ClerkProvider: (props: { publishableKey: string; children?: ReactNode }) => ReactNode;
    };
    return createElement(ClerkProvider, { publishableKey: env.clerkPublishableKey }, children);
  } catch {
    return <>{children}</>;
  }
}

export async function getClerkBearerToken(): Promise<string | null> {
  try {
    const { getClerkInstance } = require("@clerk/clerk-expo") as typeof import("@clerk/clerk-expo");
    const clerk = getClerkInstance();
    return (await clerk.session?.getToken()) ?? null;
  } catch {
    return null;
  }
}

export function getClerkPrimaryEmail(): string | null {
  try {
    const { getClerkInstance } = require("@clerk/clerk-expo") as typeof import("@clerk/clerk-expo");
    return getClerkInstance().user?.primaryEmailAddress?.emailAddress ?? null;
  } catch {
    return null;
  }
}
