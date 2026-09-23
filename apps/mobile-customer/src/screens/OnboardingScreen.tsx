import { Text, StyleSheet, Pressable } from "react-native";
import { colors, typography } from "@porterchain/mobile-theme";
import type { OnboardingStatus } from "../api";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";

type Props = {
  status: OnboardingStatus | null;
  error: string | null;
  onRefresh: () => void;
  onSignOut: () => void;
};

export function OnboardingScreen({ status, error, onRefresh, onSignOut }: Props) {
  return (
    <Screen testID="customer-onboarding">
      <Text style={styles.title}>Finish sign-in</Text>
      <Text style={styles.lede}>Porterchain checks these steps before opening your home.</Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {(status?.steps ?? []).map((step) => (
        <Text key={step.id} style={step.complete ? styles.done : styles.pending}>
          {step.complete ? "Done" : "Needed"} · {step.label}
          {step.status.startsWith("conflict_") ? " · wrong account type" : ""}
          {step.id === "portal_enabled" && !step.complete ? " · portal is turned off" : ""}
        </Text>
      ))}
      <PrimaryButton label="Check again" onPress={onRefresh} />
      <Pressable accessibilityRole="button" onPress={onSignOut}>
        <Text style={styles.signOut}>Sign out</Text>
      </Pressable>
    </Screen>
  );
}

export function AccessDeniedScreen({
  detail,
  onSignOut,
}: {
  detail: string;
  onSignOut: () => void;
}) {
  return (
    <Screen testID="customer-denied">
      <Text style={styles.title}>Access denied</Text>
      <Text style={styles.lede}>{detail}</Text>
      <Pressable accessibilityRole="button" onPress={onSignOut}>
        <Text style={styles.signOut}>Sign out</Text>
      </Pressable>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { ...typography.title, fontSize: 32, color: colors.primary },
  lede: { ...typography.body, color: colors.muted },
  done: { ...typography.caption, color: colors.success },
  pending: { ...typography.caption, color: colors.primary },
  error: { ...typography.caption, color: colors.danger },
  signOut: { ...typography.caption, color: colors.danger, textAlign: "center" },
});
