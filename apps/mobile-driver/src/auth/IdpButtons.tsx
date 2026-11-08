/**
 * Keycloak sign-in. One button opens the Porterchain page with authorization code + PKCE,
 * the same grant the website uses. Apple and Google are not separate native buttons:
 * token exchange is rejected in production, and an Apple hint would open a non-Apple page.
 */
import { useState } from "react";
import { humanError } from "../errorCopy";
import { waitForSignedSession } from "../session";
import { Button } from "../ui/kit";
import { authErrorCopy } from "./keycloak";
import { type SignInOptions, useSessionView } from "./SessionGate";

type Busy = "sign-in" | null;

export function IdpButtons({
  invite,
  onDone,
  onError,
}: {
  invite: boolean;
  onDone: () => void;
  onError: (message: string) => void;
}) {
  const { signIn } = useSessionView();
  const [busy, setBusy] = useState<Busy>(null);
  if (!signIn) return null;

  const run = async (opts: SignInOptions) => {
    setBusy("sign-in");
    try {
      await signIn(opts);
      if (!(await waitForSignedSession())) throw new Error("invalid_driver_token");
      onDone();
    } catch (err) {
      const code = err instanceof Error ? err.message : "sign_in_failed";
      onError(code === "invalid_driver_token" ? humanError(code) : authErrorCopy(code));
    } finally {
      setBusy(null);
    }
  };

  return (
    <Button
      tone="primary"
      testID="hosted-sign-in"
      label={invite ? "Accept invite" : "Sign in"}
      busy={busy === "sign-in"}
      disabled={busy != null}
      onPress={() => void run({ register: invite })}
    />
  );
}
