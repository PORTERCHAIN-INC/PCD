import { Linking, Platform, Text, StyleSheet } from "react-native";
import { colors, spacing, typography } from "@porterchain/mobile-theme";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";
import type { MobileDriverPolicy } from "../types";

type Props = {
  policy: MobileDriverPolicy;
  soft?: boolean;
  onContinue?: () => void;
};

export function ForceUpdateScreen({ policy, soft, onContinue }: Props) {
  const storeUrl = Platform.OS === "ios" ? policy.store_url_ios : policy.store_url_android;

  return (
    <Screen testID="mobile-force-update">
      <Text style={styles.title}>{soft ? "Update available" : "Update required"}</Text>
      <Text style={styles.lede}>
        {policy.message || "Please update Porterchain Driver to continue."}
      </Text>
      <Text style={styles.meta}>Minimum version {policy.min_version}</Text>
      <PrimaryButton
        label="Open store"
        onPress={() => {
          if (storeUrl) void Linking.openURL(storeUrl);
        }}
      />
      {soft && onContinue ? (
        <PrimaryButton tone="ghost" label="Continue anyway" onPress={onContinue} />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { ...typography.title, fontSize: 28, color: colors.primary },
  lede: { ...typography.body, color: colors.primary, marginTop: spacing.sm },
  meta: { ...typography.caption, color: colors.muted, marginVertical: spacing.md },
});
