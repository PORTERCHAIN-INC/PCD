/**
 * Keycloak sign-in (L36). Apple and Google same size (Guideline 4.8). Native Apple (iOS) /
 * Google first, exchanged for Keycloak tokens; Keycloak browser flow as fallback. The App Review
 * account taps "Sign in" and uses email + password on the Keycloak page (no code).
 */
import { useState } from "react";
import { Platform } from "react-native";
import * as AppleAuthentication from "expo-apple-authentication";
import { humanError } from "../errorCopy";
import { waitForSignedSession } from "../session";
import { Button } from "../ui/kit";
import { authErrorCopy, idpEnabled } from "./keycloak";
import { type SignInOptions, useSessionView } from "./SessionGate";

type Busy = "sign-in" | "apple" | "google" | null;

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

  const run = async (kind: Exclude<Busy, null>, opts: SignInOptions) => {
    setBusy(kind);
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
    <>
      <Button
        tone="primary"
        testID="hosted-sign-in"
        label={invite ? "Accept invite" : "Sign in"}
        busy={busy === "sign-in"}
        disabled={busy != null}
        onPress={() => void run("sign-in", { register: invite })}
      />
      {idpEnabled("apple") ? (
        Platform.OS === "ios" ? (
          <AppleAuthentication.AppleAuthenticationButton
            testID="apple-sign-in"
            buttonType={AppleAuthentication.AppleAuthenticationButtonType.SIGN_IN}
            buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
            cornerRadius={12}
            style={{ height: 52, width: "100%" }}
            onPress={() => void run("apple", { idpHint: "apple", native: true })}
          />
        ) : (
          <Button
            tone="secondary"
            testID="apple-sign-in"
            label="Sign in with Apple"
            busy={busy === "apple"}
            disabled={busy != null}
            onPress={() => void run("apple", { idpHint: "apple" })}
          />
        )
      ) : null}
      {idpEnabled("google") ? (
        <Button
          tone="secondary"
          testID="google-sign-in"
          label="Sign in with Google"
          busy={busy === "google"}
          disabled={busy != null}
          onPress={() => void run("google", { idpHint: "google", native: true })}
        />
      ) : null}
    </>
  );
}
