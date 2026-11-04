import { captureRequestError } from "@porterchain/config/glitchtip/portal";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("../glitchtip.server.config");
  }
}

export const onRequestError = captureRequestError;
