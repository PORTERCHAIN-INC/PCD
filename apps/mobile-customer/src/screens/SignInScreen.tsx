import { useState } from "react";
import { View } from "react-native";
import { useHostedAuth } from "@clerk/expo/hosted-auth";
import { useSessionView } from "../auth/SessionGate";
import { allowDevAuth, apiBaseUrl, clerkPublishableKey } from "../config";
import { humanCustomerError } from "../errors";
import { clearSession, waitForSignedSession } from "../session";
import { Motion } from "../ui/Motion";
import { PrimaryButton } from "../ui/PrimaryButton";
import { spacing } from "../theme";
import { Banner, Button, Txt } from "../ui/kit";
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
        label="Sign in"
        loading={busy === "sign-in"}
        disabled={busy != null}
        onPress={() => void start("sign-in")}
      />
      <PrimaryButton
        testID="customer-sign-up"
        tone="ghost"
        label="Create account"
        loading={busy === "sign-up"}
        disabled={busy != null}
        onPress={() => void start("sign-up")}
      />
      {error ? <Banner tone="danger" text={error} /> : null}
    </>
  );
}

export function SignInScreen({ apiUp, onSignedIn, onTrack }: Props) {
  const session = useSessionView();
  const [signingOut, setSigningOut] = useState(false);
  const showHosted = Boolean(clerkPublishableKey);
  const stuckSession = session.signedIn && showHosted;

  return (
    <Screen testID="mobile-sign-in" scroll style={{ flexGrow: 1, justifyContent: "center" }}>
      <Motion name="route" size={200} />
      <View style={{ gap: spacing.sm }}>
        <Txt v="overline" tone="accent">
          PorterChain
        </Txt>
        <Txt v="largeTitle" accessibilityRole="header">
          Same-day delivery, booked in a minute.
        </Txt>
        <Txt v="body" tone="muted">
          Get an upfront price with HST, pay by card, and follow every handoff live.
        </Txt>
      </View>
      {__DEV__ ? (
        <Txt v="caption" tone="muted">
          API {apiUp == null ? "…" : apiUp ? "reachable" : "unreachable"} · {apiBaseUrl}
        </Txt>
      ) : null}
      {session.bootError ? <Banner tone="danger" text={session.bootError} /> : null}
      <View style={{ gap: spacing.sm, marginTop: spacing.md }}>
        {showHosted && !stuckSession ? <HostedButtons onSignedIn={onSignedIn} /> : null}
        {!showHosted && allowDevAuth() ? (
          <PrimaryButton testID="dev-sign-in" label="Continue" onPress={onSignedIn} />
        ) : null}
        {!showHosted && !allowDevAuth() ? (
          <Banner
            tone="danger"
            text="This build has no PorterChain Platform key. Archive with the live publishable key."
          />
        ) : null}
        {stuckSession ? (
          <>
            <Txt v="callout" tone="muted">
              A session is already on this device.
            </Txt>
            <PrimaryButton label="Continue" onPress={onSignedIn} />
            <Button
              variant="plain"
              label="Sign out"
              loading={signingOut}
              onPress={() => {
                setSigningOut(true);
                void clearSession().finally(() => setSigningOut(false));
              }}
            />
          </>
        ) : null}
        <Button
          variant="plain"
          icon="locate-outline"
          label="Track a shipment without an account"
          onPress={onTrack}
        />
      </View>
    </Screen>
  );
}
