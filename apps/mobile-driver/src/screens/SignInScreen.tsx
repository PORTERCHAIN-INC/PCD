import { useEffect, useRef, useState } from "react";
import { Text, StyleSheet } from "react-native";
import { useHostedAuth } from "@clerk/expo/hosted-auth";
import { colors, typography } from "@porterchain/mobile-theme";
import { unlockWithDeviceAuth } from "../auth/deviceUnlock";
import { useSessionView } from "../auth/SessionGate";
import { humanDriverError } from "../auth/errors";
import { allowDevAuth, clerkPublishableKey, isStoreProfile } from "../config";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";
import { StatusRail } from "../ui/StatusRail";
import type { Handshake } from "../types";

type Props = {
  handshake: Handshake;
  probing: boolean;
  onContinue: () => void;
};

function HostedSignIn({ onDone }: { onDone: () => void }) {
  const { startHostedAuth } = useHostedAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <>
      <PrimaryButton
        label={busy ? "Opening sign-in…" : "Sign in with Porterchain"}
        disabled={busy}
        onPress={() => {
          setBusy(true);
          setError(null);
          void startHostedAuth({ mode: "sign-in" })
            .then(() => onDone())
            .catch((err: unknown) => {
              setError(humanDriverError(err instanceof Error ? err.message : "sign_in_failed"));
            })
            .finally(() => setBusy(false));
        }}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </>
  );
}

/**
 * Daily path: Clerk tokenCache restore → optional biometric → handshake.
 * Hosted browser only when the Clerk session is dead.
 */
export function SignInScreen({ handshake, probing, onContinue }: Props) {
  const session = useSessionView();
  const canDev = allowDevAuth();
  const storeBlocked = isStoreProfile && !clerkPublishableKey;
  const needHosted = Boolean(clerkPublishableKey) && session.ready && !session.signedIn && !canDev;
  const canUnlock = session.ready && (session.signedIn || canDev) && !storeBlocked;
  const continueDisabled = probing || storeBlocked || (!canUnlock && needHosted);
  const autoTried = useRef(false);
  const [unlockHint, setUnlockHint] = useState<string | null>(null);
  const [unlockError, setUnlockError] = useState<string | null>(null);

  useEffect(() => {
    if (autoTried.current || probing || storeBlocked) return;
    if (!session.ready) return;
    if (!session.signedIn && !canDev) return;
    autoTried.current = true;
    void (async () => {
      setUnlockError(null);
      if (session.signedIn && !canDev) {
        setUnlockHint("Confirm with Face ID / fingerprint…");
        const unlock = await unlockWithDeviceAuth();
        setUnlockHint(null);
        if (!unlock.ok) {
          autoTried.current = false;
          setUnlockError(
            unlock.reason === "unlock_cancelled"
              ? "Unlock cancelled — tap Continue to try again."
              : "Could not unlock this device. Tap Continue to retry."
          );
          return;
        }
        if (!unlock.skipped) {
          setUnlockHint("Unlocked — handshaking…");
        } else {
          setUnlockHint("Session restored — unlocking…");
        }
      }
      onContinue();
    })();
  }, [canDev, onContinue, probing, session.ready, session.signedIn, storeBlocked]);

  return (
    <Screen testID="mobile-sign-in">
      <Text style={styles.kicker}>Porterchain</Text>
      <Text style={styles.title}>Driver</Text>
      <Text style={styles.lede}>Assigned work. Push when it changes. GPS stays in Fleetbase.</Text>
      <StatusRail handshake={handshake} />
      {handshake.error ? (
        <Text style={styles.error}>{humanDriverError(handshake.error)}</Text>
      ) : null}
      {unlockError ? <Text style={styles.error}>{unlockError}</Text> : null}
      {storeBlocked ? (
        <Text style={styles.error}>
          Sign-in is unavailable on this build. Contact Porterchain operations.
        </Text>
      ) : null}
      <Text style={styles.pushDetail}>{handshake.push.detail}</Text>
      {unlockHint ? (
        <Text style={styles.restore} testID="session-restored">
          {unlockHint}
        </Text>
      ) : null}
      {needHosted ? <HostedSignIn onDone={onContinue} /> : null}
      <PrimaryButton
        testID="dev-sign-in"
        label={
          probing
            ? "Handshaking…"
            : session.signedIn
              ? "Continue"
              : canDev
                ? "Continue"
                : needHosted
                  ? "Sign in required"
                  : "Continue"
        }
        disabled={continueDisabled}
        onPress={() => {
          setUnlockError(null);
          if (session.signedIn && !canDev) {
            void unlockWithDeviceAuth().then((unlock) => {
              if (!unlock.ok) {
                setUnlockError(
                  unlock.reason === "unlock_cancelled"
                    ? "Unlock cancelled — try again."
                    : "Could not unlock this device."
                );
                return;
              }
              onContinue();
            });
            return;
          }
          onContinue();
        }}
      />
      <Text style={styles.footnote}>
        {canDev
          ? "Local: Bearer dev → first approved driver after API handshake. Store builds require Clerk."
          : session.signedIn
            ? "Returning driver: biometric unlock when available, then saved Clerk session."
            : "Production: Clerk session is the API bearer. Handshake must succeed before work."}
      </Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  kicker: {
    ...typography.caption,
    color: colors.driverGreen,
    fontWeight: "700",
    letterSpacing: 1.2,
    textTransform: "uppercase",
  },
  title: {
    ...typography.title,
    fontSize: 34,
    color: colors.primary,
  },
  lede: {
    ...typography.body,
    color: colors.muted,
    maxWidth: 320,
  },
  error: {
    ...typography.caption,
    color: colors.danger,
  },
  restore: {
    ...typography.caption,
    color: colors.driverGreen,
    fontWeight: "600",
  },
  pushDetail: {
    ...typography.caption,
    color: colors.muted,
  },
  footnote: {
    ...typography.caption,
    color: colors.muted,
    marginTop: "auto",
  },
});
