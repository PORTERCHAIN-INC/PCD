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
      ClerkProvider: (props: {
        publishableKey: string;
        tokenCache?: unknown;
        children?: ReactNode;
      }) => ReactNode;
    };
    let tokenCache: unknown;
    try {
      tokenCache = (require("@clerk/clerk-expo/token-cache") as { tokenCache: unknown }).tokenCache;
    } catch {
      tokenCache = undefined;
    }
    return createElement(ClerkProvider, {
      publishableKey: env.clerkPublishableKey,
      ...(tokenCache ? { tokenCache } : {}),
      children,
    });
  } catch {
    return <>{children}</>;
  }
}

async function readClerkSessionToken(): Promise<string | null> {
  const { getClerkInstance } = require("@clerk/clerk-expo") as typeof import("@clerk/clerk-expo");
  const clerk = getClerkInstance();
  return (await clerk.session?.getToken()) ?? null;
}

export async function getClerkBearerToken(maxAttempts = 8): Promise<string | null> {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const token = await readClerkSessionToken();
      if (token) return token;
    } catch {
      // Clerk may not be ready immediately after setActive.
    }
    if (attempt < maxAttempts - 1) {
      await new Promise((resolve) => setTimeout(resolve, 75 * (attempt + 1)));
    }
  }
  return null;
}

export function getClerkPrimaryEmail(): string | null {
  try {
    const { getClerkInstance } = require("@clerk/clerk-expo") as typeof import("@clerk/clerk-expo");
    return getClerkInstance().user?.primaryEmailAddress?.emailAddress ?? null;
  } catch {
    return null;
  }
}
