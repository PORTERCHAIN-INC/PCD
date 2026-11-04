/**
 * Keycloak sign-in buttons (L36). Apple and Google are the same size (Guideline 4.8 / A-APR-04).
 * Native Apple (iOS) / Google first, exchanged for Keycloak tokens; Keycloak browser flow as
 * fallback. The App Review account uses "Sign in" (email + password on the Keycloak page, no code).
 */
import { useState } from "react";
import { Platform } from "react-native";
import * as AppleAuthentication from "expo-apple-authentication";
import { humanCustomerError } from "../errors";
import { waitForSignedSession } from "../session";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Banner } from "../ui/kit";
import { authErrorCopy, idpEnabled } from "./keycloak";
import { type SignInOptions, useSessionView } from "./SessionGate";

type Busy = "sign-in" | "sign-up" | "apple" | "google" | null;

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
      {idpEnabled("apple") ? (
        Platform.OS === "ios" ? (
          <AppleAuthentication.AppleAuthenticationButton
            testID="apple-sign-in"
            buttonType={AppleAuthentication.AppleAuthenticationButtonType.SIGN_IN}
            buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
            cornerRadius={10}
            style={{ height: 50, width: "100%" }}
            onPress={() => void run("apple", { idpHint: "apple", native: true })}
          />
        ) : (
          <PrimaryButton
            testID="apple-sign-in"
            tone="ghost"
            label="Sign in with Apple"
            loading={busy === "apple"}
            disabled={busy != null}
            onPress={() => void run("apple", { idpHint: "apple" })}
          />
        )
      ) : null}
      {idpEnabled("google") ? (
        <PrimaryButton
          testID="google-sign-in"
          tone="ghost"
          label="Sign in with Google"
          loading={busy === "google"}
          disabled={busy != null}
          onPress={() => void run("google", { idpHint: "google", native: true })}
        />
      ) : null}
      {error ? <Banner tone="danger" text={error} /> : null}
    </>
  );
}
