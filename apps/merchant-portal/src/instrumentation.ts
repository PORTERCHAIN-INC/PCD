import * as Sentry from "@sentry/nextjs";
import { clerkDevBypassIgnored } from "@porterchain/auth/devBypass";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("../sentry.server.config");
    // A leaked NEXT_PUBLIC_CLERK_DEV_BYPASS is refused, not honoured. Say so once
    // at boot, or the deploy just looks like an unexplained wall of 401s (BJ).
    if (clerkDevBypassIgnored()) {
      console.warn(
        "[auth] NEXT_PUBLIC_CLERK_DEV_BYPASS is set but ignored: this is a production build. " +
          "Unset it and configure Clerk keys."
      );
    }
  }
}

export const onRequestError = Sentry.captureRequestError;
