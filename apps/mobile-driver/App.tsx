import { useState } from "react";
import { StatusBar } from "expo-status-bar";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { colors, radius, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";

type Screen = "sign-in" | "track";

export default function App() {
  const [screen, setScreen] = useState<Screen>("sign-in");

  if (screen === "sign-in") {
    return (
      <View style={styles.container} testID="mobile-sign-in">
        <Text style={styles.title}>Sign in</Text>
        <Text style={[styles.subtitle, styles.driverAccent]}>Porterchain Driver</Text>
        <Pressable
          accessibilityRole="button"
          style={styles.button}
          testID="dev-sign-in"
          onPress={() => setScreen("track")}
        >
          <Text style={styles.buttonText}>Continue (dev)</Text>
        </Pressable>
        <StatusBar style="auto" />
      </View>
    );
  }

  return (
    <View style={styles.container} testID="mobile-track">
      <Text style={styles.title}>Active route</Text>
      <Text style={styles.subtitle} testID="route-status">
        1 stop · en route to pickup
      </Text>
      <Pressable accessibilityRole="button" style={styles.button} testID="track-refresh">
        <Text style={styles.buttonText}>Refresh GPS</Text>
      </Pressable>
      <StatusBar style="auto" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.grayBg,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.md,
    padding: spacing.xl,
  },
  title: {
    ...typography.title,
    color: colors.primary,
  },
  subtitle: {
    ...typography.caption,
    color: colors.muted,
    textAlign: "center",
  },
  driverAccent: {
    color: colors.driverGreen,
    fontWeight: "600",
  },
  button: {
    backgroundColor: colors.secondary,
    borderRadius: radius.lg,
    minHeight: touchTargetMin,
    justifyContent: "center",
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
  },
  buttonText: {
    ...typography.button,
    color: colors.white,
  },
});
