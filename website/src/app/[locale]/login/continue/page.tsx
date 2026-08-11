"use client";

/**
 * Post-Clerk continue — no SignIn widget, no #/factor-one.
 * Resolves session-context and sends the user to their module.
 */

import { Suspense } from "react";
import PostAuthPortalRedirect from "@/components/portal/PostAuthPortalRedirect";

export default function LoginContinuePage() {
  return (
    <Suspense fallback={null}>
      <PostAuthPortalRedirect />
    </Suspense>
  );
}
