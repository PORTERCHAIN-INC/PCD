"use client";

/**
 * Post-Clerk continue — no SignIn widget, no #/factor-one.
 * Resolves session-context and sends the user to their module.
 */

import PostAuthPortalRedirect from "@/components/portal/PostAuthPortalRedirect";

export default function LoginContinuePage() {
  return <PostAuthPortalRedirect />;
}
