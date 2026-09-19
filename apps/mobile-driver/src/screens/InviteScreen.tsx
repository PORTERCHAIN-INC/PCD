import { useState } from "react";
import { Text, StyleSheet } from "react-native";
import { useHostedAuth } from "@clerk/expo/hosted-auth";
import { colors, typography } from "@porterchain/mobile-theme";
import { clerkPublishableKey } from "../config";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";

type Props = {
  inviteToken: string | null;
  error?: string | null;
  onContinue: () => void;
};

function HostedInvite({ onContinue }: { onContinue: () => void }) {
  const { startHostedAuth } = useHostedAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <>
      <PrimaryButton
        testID="accept-invite-dev"
        label={busy ? "Opening sign-in…" : "Accept invite"}
        disabled={busy}
        onPress={() => {
          setBusy(true);
          setError(null);
          void startHostedAuth({ mode: "sign-up" })
            .then(() => onContinue())
            .catch((err: unknown) => {
              setError(err instanceof Error ? err.message : "invite_failed");
            })
            .finally(() => setBusy(false));
        }}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </>
  );
}

export function InviteScreen({ inviteToken, error, onContinue }: Props) {
  return (
    <Screen testID="mobile-driver-invite">
      <Text style={styles.kicker}>Invite</Text>
      <Text style={styles.title}>Driver invite</Text>
      <Text style={styles.lede}>
        Clerk completes the invite. Work opens only after the API handshake.
      </Text>
      <Text style={styles.token} testID="invite-token">
        Token: {inviteToken ?? "—"}
      </Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {clerkPublishableKey ? (
        <HostedInvite onContinue={onContinue} />
      ) : (
        <PrimaryButton testID="accept-invite-dev" label="Continue setup" onPress={onContinue} />
      )}
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
  },
  token: {
    ...typography.caption,
    color: colors.secondary,
  },
  error: {
    ...typography.caption,
    color: colors.danger,
  },
});
