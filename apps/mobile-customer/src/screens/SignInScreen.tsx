import { useState } from "react";
import { View } from "react-native";
import { IdpButtons } from "../auth/IdpButtons";
import { useSessionView } from "../auth/SessionGate";
import { allowDevAuth, apiBaseUrl } from "../config";
import { clearSession } from "../session";
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

export function SignInScreen({ apiUp, onSignedIn, onTrack }: Props) {
  const session = useSessionView();
  const [signingOut, setSigningOut] = useState(false);
  const showHosted = Boolean(session.signIn);
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
          Get an upfront price, pay by card, and follow every handoff live.
        </Txt>
      </View>
      {__DEV__ ? (
        <Txt v="caption" tone="muted">
          API {apiUp == null ? "…" : apiUp ? "reachable" : "unreachable"} · {apiBaseUrl}
        </Txt>
      ) : null}
      {session.bootError ? <Banner tone="danger" text={session.bootError} /> : null}
      <View style={{ gap: spacing.sm, marginTop: spacing.md }}>
        {showHosted && !stuckSession ? (
          <>
            <IdpButtons onSignedIn={onSignedIn} />
          </>
        ) : null}
        {!showHosted && allowDevAuth() ? (
          <PrimaryButton testID="dev-sign-in" label="Continue" onPress={onSignedIn} />
        ) : null}
        {!showHosted && !allowDevAuth() ? (
          <Banner
            tone="danger"
            text="This build has no sign-in server configured. Archive with EXPO_PUBLIC_KEYCLOAK_URL set."
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
