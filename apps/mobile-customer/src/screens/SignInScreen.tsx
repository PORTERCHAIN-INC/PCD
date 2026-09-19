import { Text, StyleSheet } from "react-native";
import { colors, typography } from "@porterchain/mobile-theme";
import { apiBaseUrl } from "../config";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";

type Props = {
  apiUp: boolean | null;
  onContinue: () => void;
};

export function SignInScreen({ apiUp, onContinue }: Props) {
  return (
    <Screen testID="mobile-sign-in">
      <Text style={styles.kicker}>Porterchain</Text>
      <Text style={styles.title}>Track a shipment</Text>
      <Text style={styles.lede}>Look up a tracking number. No account required.</Text>
      <Text style={styles.meta}>
        API {apiUp == null ? "…" : apiUp ? "reachable" : "unreachable"} · {apiBaseUrl}
      </Text>
      <PrimaryButton testID="dev-sign-in" label="Continue" onPress={onContinue} />
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
  title: {
    ...typography.title,
    fontSize: 34,
    color: colors.primary,
  },
  lede: {
    ...typography.body,
    color: colors.muted,
  },
  meta: {
    ...typography.caption,
    color: colors.muted,
  },
});
