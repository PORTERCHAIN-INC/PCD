"use client";

import type { ReactNode } from "react";
import { AppAuthProvider } from "@porterchain/auth";

/**
 * Keycloak session (pc-website) for the auth routes only (/login, /sign-up). Marketing pages
 * render without it; the navbar shows a plain "Log in" link there.
 */
export default function AuthShellProvider({ children }: { children: ReactNode; locale?: string }) {
  return <AppAuthProvider>{children}</AppAuthProvider>;
}
