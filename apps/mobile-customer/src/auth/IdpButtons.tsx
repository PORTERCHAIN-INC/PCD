/**
 * Keycloak sign-in. One path: the Porterchain page with authorization code + PKCE,
 * the same grant the website uses. Native Apple/Google token exchange is not used.
 * Sign in with Apple is not offered here because the live page has no Apple provider.
 */
import { useState } from "react";
import { humanCustomerError } from "../errors";
import { waitForSignedSession } from "../session";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Banner, Txt } from "../ui/kit";
import { authErrorCopy } from "./keycloak";
import { type SignInOptions, useSessionView } from "./SessionGate";

type Busy = "sign-in" | "sign-up" | null;

export function IdpButtons({ onSignedIn }: { onSignedIn: () => void }) {
  const { signIn } = useSessionView();
  const [busy, setBusy] = useState<Busy>(null);
  const [error, setError] = useState<string | null>(null);
  if (!signIn) return null;

  async function run(kind: Exclude<Busy, null>, opts: SignInOptions) {
    setBusy(kind);
    setError(null);
    try {
      await signIn!(opts);
      if (!(await waitForSignedSession())) throw new Error("signed_out");
      onSignedIn();
    } catch (err) {
      const code = err instanceof Error ? err.message : "sign_in_failed";
      setError(code === "signed_out" ? humanCustomerError(code) : authErrorCopy(code));
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PrimaryButton
        testID="customer-sign-in"
        label="Sign in"
        loading={busy === "sign-in"}
        disabled={busy != null}
        onPress={() => void run("sign-in", {})}
      />
      <PrimaryButton
        testID="customer-sign-up"
        tone="ghost"
        label="Create account"
        loading={busy === "sign-up"}
        disabled={busy != null}
        onPress={() => void run("sign-up", { register: true })}
      />
      <Txt v="caption" tone="muted">
        This opens the Porterchain page. Use your email and password, or Google on that page. Skip
        any link that says existing PorterChain sign-in. Sign in with Apple is not on that page.
      </Txt>
      {error ? <Banner tone="danger" text={error} /> : null}
    </>
  );
}
