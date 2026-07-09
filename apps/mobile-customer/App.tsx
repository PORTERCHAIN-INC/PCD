import { useState } from "react";
import { StatusBar } from "expo-status-bar";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { colors, radius, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";

type Screen = "sign-in" | "track";

export default function App() {
  const [screen, setScreen] = useState<Screen>("sign-in");
  const [trackingNumber, setTrackingNumber] = useState("");

  if (screen === "sign-in") {
    return (
      <View style={styles.container} testID="mobile-sign-in">
        <Text style={styles.title}>Sign in</Text>
        <Text style={styles.subtitle}>Porterchain Customer</Text>
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
      <Text style={styles.title}>Track delivery</Text>
      <TextInput
        accessibilityLabel="Tracking number"
        placeholder="Tracking number"
        placeholderTextColor={colors.muted}
        style={styles.input}
        testID="tracking-input"
        value={trackingNumber}
        onChangeText={setTrackingNumber}
      />
      <Pressable
        accessibilityRole="button"
        style={styles.button}
        testID="track-lookup"
        onPress={() => undefined}
      >
        <Text style={styles.buttonText}>
          {trackingNumber.trim() ? `Track ${trackingNumber.trim()}` : "Enter a tracking number"}
        </Text>
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
  },
  input: {
    width: "100%",
    maxWidth: 320,
    minHeight: touchTargetMin,
    borderWidth: 1,
    borderColor: `${colors.primary}26`,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontSize: typography.body.fontSize,
    backgroundColor: colors.white,
    color: colors.primary,
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
