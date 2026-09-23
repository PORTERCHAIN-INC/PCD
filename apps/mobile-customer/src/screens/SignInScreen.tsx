import { useState } from "react";
import { Text, StyleSheet, Pressable } from "react-native";
import { useHostedAuth } from "@clerk/expo/hosted-auth";
import { colors, typography } from "@porterchain/mobile-theme";
import { useSessionView } from "../auth/SessionGate";
import { allowDevAuth, apiBaseUrl, clerkPublishableKey } from "../config";
import { humanCustomerError } from "../errors";
import { clearSession, waitForSignedSession } from "../session";
import { Motion } from "../ui/Motion";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";

type Props = {
  apiUp: boolean | null;
  onSignedIn: () => void;
  onTrack: () => void;
};

function HostedButtons({ onSignedIn }: { onSignedIn: () => void }) {
  const { startHostedAuth } = useHostedAuth();
  const [busy, setBusy] = useState<"sign-in" | "sign-up" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function start(mode: "sign-in" | "sign-up") {
    setBusy(mode);
    setError(null);
    try {
      await startHostedAuth({ mode });
      const ready = await waitForSignedSession();
      if (!ready) throw new Error("signed_out");
      onSignedIn();
    } catch (err) {
      setError(humanCustomerError(err instanceof Error ? err.message : "sign_in_failed"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PrimaryButton
        testID="customer-sign-in"
        label={busy === "sign-in" ? "Opening sign-in…" : "Sign in"}
        disabled={busy != null}
        onPress={() => void start("sign-in")}
      />
      <PrimaryButton
        testID="customer-sign-up"
        tone="ghost"
        label={busy === "sign-up" ? "Opening sign-up…" : "Create account"}
        disabled={busy != null}
        onPress={() => void start("sign-up")}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </>
  );
}

export function SignInScreen({ apiUp, onSignedIn, onTrack }: Props) {
  const session = useSessionView();
  const [signingOut, setSigningOut] = useState(false);
  const showHosted = Boolean(clerkPublishableKey);
  const stuckSession = session.signedIn && showHosted;

  return (
    <Screen testID="mobile-sign-in">
      <Motion name="route" size={220} />
      <Text style={styles.kicker}>Porterchain</Text>
      <Text style={styles.title}>Capacity when you need it.</Text>
      <Text style={styles.lede}>Quote a lane, book the delivery, and follow every handoff.</Text>
      {__DEV__ ? (
        <Text style={styles.meta}>
          API {apiUp == null ? "…" : apiUp ? "reachable" : "unreachable"} · {apiBaseUrl}
        </Text>
      ) : null}
      {session.bootError ? <Text style={styles.error}>{session.bootError}</Text> : null}
      {showHosted && !stuckSession ? <HostedButtons onSignedIn={onSignedIn} /> : null}
      {!showHosted && allowDevAuth() ? (
        <PrimaryButton testID="dev-sign-in" label="Continue" onPress={onSignedIn} />
      ) : null}
      {!showHosted && !allowDevAuth() ? (
        <Text style={styles.error}>
          This build has no PorterChain Platform key. Archive with the live publishable key.
        </Text>
      ) : null}
      {stuckSession ? (
        <>
          <Text style={styles.lede}>A session is already on this device.</Text>
          <PrimaryButton label="Continue" onPress={onSignedIn} />
          <Pressable
            accessibilityRole="button"
            disabled={signingOut}
            onPress={() => {
              setSigningOut(true);
              void clearSession().finally(() => setSigningOut(false));
            }}
          >
            <Text style={styles.signOut}>{signingOut ? "Signing out…" : "Sign out"}</Text>
          </Pressable>
        </>
      ) : null}
      <Pressable accessibilityRole="button" onPress={onTrack}>
        <Text style={styles.link}>Track a shipment without an account</Text>
      </Pressable>
    </Screen>
  );
}

const styles = StyleSheet.create({
  kicker: {
    ...typography.caption,
    color: colors.secondary,
    fontWeight: "700",
    letterSpacing: 1.2,
    textTransform: "uppercase",
  },
  title: { ...typography.title, fontSize: 34, color: colors.primary },
  lede: { ...typography.body, color: colors.muted },
  meta: { ...typography.caption, color: colors.muted },
  error: { ...typography.caption, color: colors.danger },
  signOut: { ...typography.caption, color: colors.danger, textAlign: "center" },
  link: { ...typography.caption, color: colors.secondary, textAlign: "center" },
});
