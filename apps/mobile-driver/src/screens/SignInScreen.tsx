/**
 * Daily path: saved session → Face ID / fingerprint → handshake, with no taps.
 * Keycloak sign-in only when there is no live session. An invite link switches it to sign-up.
 */
import { useEffect, useRef, useState } from "react";
import { StyleSheet, View } from "react-native";
import { unlockWithDeviceAuth } from "../auth/deviceUnlock";
import { IdpButtons } from "../auth/IdpButtons";
import { useSessionView } from "../auth/SessionGate";
import { allowDevAuth, isStoreProfile } from "../config";
import { humanError, needsAccountSwitch } from "../errorCopy";
import { Banner, Body, Button, Label, Muted, Screen, Title } from "../ui/kit";
import { color, space, type } from "../ui/theme";

type Props = {
  error: string | null;
  probing: boolean;
  inviteToken: string | null;
  onContinue: () => void;
  onSignOut: () => Promise<void>;
};

function unlockCopy(reason: string | undefined): string {
  return reason === "unlock_cancelled"
    ? "Unlock cancelled. Tap Continue to try again."
    : "Could not unlock this phone. Tap Continue to retry.";
}

export function SignInScreen({ error, probing, inviteToken, onContinue, onSignOut }: Props) {
  const session = useSessionView();
  const canDev = allowDevAuth();
  const storeBlocked = isStoreProfile && !session.signIn;
  const needHosted = Boolean(session.signIn) && session.ready && !session.signedIn && !canDev;
  const switchAccount = session.signedIn && needsAccountSwitch(error);
  const autoTried = useRef(false);
  const [hint, setHint] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);

  const resetSignIn = async () => {
    if (!session.resetSignIn) return;
    setResetting(true);
    setLocalError(null);
    try {
      await session.resetSignIn();
      setHint(
        "Sign-in on this phone was reset. If a Porterchain page opened, confirm sign-out. Then tap Sign in and use your email and password. Jobs and proof photos on this phone were kept."
      );
    } catch {
      setLocalError("Could not finish reset. Tap Sign in and use your email and password.");
    } finally {
      setResetting(false);
    }
  };

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
          <>
            <IdpButtons
              invite={Boolean(inviteToken)}
              onDone={onContinue}
              onError={(message) => {
                setHint(null);
                setLocalError(message);
              }}
            />
            {session.resetSignIn ? (
              <Button
                tone="quiet"
                testID="reset-sign-in"
                label="Reset sign-in on this phone"
                hint="Clears the Porterchain sign-in on this phone. Jobs and proof photos saved here stay here."
                busy={resetting}
                disabled={resetting}
                onPress={() => void resetSignIn()}
              />
            ) : null}
          </>
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
      {needHosted ? (
        <Muted>
          Sign in opens the Porterchain page. Use your email and password, or Google on that page.
          Skip any link that says existing PorterChain sign-in. Sign in with Apple is not available
          on that page.
        </Muted>
      ) : null}
      {shownError ? <Banner tone="danger" title={shownError} /> : null}
      {shownError && session.resetSignIn ? (
        <Muted>
          Reset sign-in clears the saved sign-in on this phone only. Jobs and proof photos saved
          here stay here.
        </Muted>
      ) : null}
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
