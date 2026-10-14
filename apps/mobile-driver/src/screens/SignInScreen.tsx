/**
 * Daily path: saved session → Face ID / fingerprint → handshake, with no taps.
 * Hosted sign-in only when there is no live session. An invite link switches it to sign-up.
 */
import { useEffect, useRef, useState } from "react";
import { StyleSheet, View } from "react-native";
import { useHostedAuth } from "@clerk/expo/hosted-auth";
import { unlockWithDeviceAuth } from "../auth/deviceUnlock";
import { useSessionView } from "../auth/SessionGate";
import { allowDevAuth, clerkPublishableKey, isStoreProfile } from "../config";
import { humanError, needsAccountSwitch } from "../errorCopy";
import { waitForSignedSession } from "../session";
import { Banner, Body, Button, Label, Muted, Screen, Title } from "../ui/kit";
import { color, space, type } from "../ui/theme";

type Props = {
  error: string | null;
  probing: boolean;
  inviteToken: string | null;
  onContinue: () => void;
  onSignOut: () => Promise<void>;
};

/** Mounted only when Clerk is configured (the hook needs ClerkProvider). */
function HostedSignIn({
  invite,
  onDone,
  onError,
}: {
  invite: boolean;
  onDone: () => void;
  onError: (code: string) => void;
}) {
  const { startHostedAuth } = useHostedAuth();
  const [busy, setBusy] = useState(false);
  return (
    <Button
      tone="primary"
      testID="hosted-sign-in"
      label={invite ? "Accept invite" : "Sign in"}
      busy={busy}
      onPress={() => {
        setBusy(true);
        void startHostedAuth({ mode: invite ? "sign-up" : "sign-in" })
          .then(async () => {
            if (!(await waitForSignedSession())) throw new Error("invalid_driver_token");
            onDone();
          })
          .catch((err: unknown) => onError(err instanceof Error ? err.message : "sign_in_failed"))
          .finally(() => setBusy(false));
      }}
    />
  );
}

function unlockCopy(reason: string | undefined): string {
  return reason === "unlock_cancelled"
    ? "Unlock cancelled. Tap Continue to try again."
    : "Could not unlock this phone. Tap Continue to retry.";
}

export function SignInScreen({ error, probing, inviteToken, onContinue, onSignOut }: Props) {
  const session = useSessionView();
  const canDev = allowDevAuth();
  const storeBlocked = isStoreProfile && !clerkPublishableKey;
  const needHosted = Boolean(clerkPublishableKey) && session.ready && !session.signedIn && !canDev;
  const switchAccount = session.signedIn && needsAccountSwitch(error);
  const autoTried = useRef(false);
  const [hint, setHint] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (!session.signedIn) autoTried.current = false;
  }, [session.signedIn]);

  const unlockThenContinue = async () => {
    setLocalError(null);
    if (session.signedIn && !canDev) {
      setHint("Confirm with Face ID or fingerprint…");
      const unlock = await unlockWithDeviceAuth();
      setHint(null);
      if (!unlock.ok) {
        autoTried.current = false;
        setLocalError(unlockCopy(unlock.reason));
        return;
      }
    }
    onContinue();
  };

  // Returning driver: try once automatically.
  useEffect(() => {
    if (autoTried.current || probing || storeBlocked || session.bootError || switchAccount) return;
    if (!session.ready || (!session.signedIn && !canDev)) return;
    autoTried.current = true;
    void unlockThenContinue();
  }, [
    canDev,
    probing,
    session.bootError,
    session.ready,
    session.signedIn,
    storeBlocked,
    switchAccount,
  ]);

  const shownError =
    localError ??
    session.bootError ??
    (error && (session.signedIn || canDev) ? humanError(error) : null);

  return (
    <Screen
      testID="mobile-sign-in"
      footer={
        switchAccount ? (
          <Button
            tone="primary"
            testID="sign-out"
            label="Sign out and use another account"
            onPress={() => void onSignOut()}
          />
        ) : needHosted ? (
          <HostedSignIn
            invite={Boolean(inviteToken)}
            onDone={onContinue}
            onError={(code) => setLocalError(humanError(code))}
          />
        ) : (
          <Button
            tone="primary"
            testID="dev-sign-in"
            label="Continue"
            busy={probing}
            disabled={storeBlocked || !session.ready}
            onPress={() => void unlockThenContinue()}
          />
        )
      }
    >
      <View style={styles.brand}>
        <Label style={styles.kicker}>PorterChain</Label>
        <Title style={styles.title}>Driver</Title>
        <Body>
          {inviteToken
            ? "You've been invited to drive with PorterChain. Accept to create your account."
            : "Your jobs, stops and proof of delivery in one place."}
        </Body>
      </View>
      {hint ? <Banner tone="info" title={hint} testID="session-restored" /> : null}
      {storeBlocked ? (
        <Banner tone="danger" title="Sign-in is unavailable on this build. Call dispatch." />
      ) : null}
      {shownError ? <Banner tone="danger" title={shownError} /> : null}
      {switchAccount ? (
        <Muted>
          You're signed in, but this account has no driver profile. Sign out, then use the email
          dispatch has on file.
        </Muted>
      ) : null}
      {canDev ? <Muted>Development build: signs in as the first approved driver.</Muted> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  brand: { gap: space.sm, paddingTop: space.xxl },
  kicker: { color: color.primary },
  title: { ...type.display, fontSize: 44, lineHeight: 50 },
});
