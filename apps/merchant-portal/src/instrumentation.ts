import { captureRequestError } from "@porterchain/config/glitchtip/portal";
import { authDevBypassIgnored } from "@porterchain/auth/devBypass";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("../glitchtip.server.config");
    // A leaked NEXT_PUBLIC_AUTH_DEV_BYPASS is refused, not honoured. Say so once
    // at boot, or the deploy just looks like an unexplained wall of 401s (BJ).
    if (authDevBypassIgnored()) {
      console.warn(
        "[auth] NEXT_PUBLIC_AUTH_DEV_BYPASS is set but ignored: this is a production build. " +
          "Unset it and configure Keycloak keys."
      );
    }
  }
}

export const onRequestError = captureRequestError;
