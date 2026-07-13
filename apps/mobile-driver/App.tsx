import { useEffect, useState } from "react";
import { StatusBar } from "expo-status-bar";
import * as Linking from "expo-linking";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { colors, radius, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";

type Screen = "sign-in" | "invite" | "route";

function parseInviteUrl(url: string | null): string | null {
  if (!url) return null;
  const parsed = Linking.parse(url);
  if (!(parsed.path ?? "").includes("driver-invite")) return null;
  const query = parsed.queryParams ?? {};
  const token = query.token;
  return typeof token === "string" ? token : null;
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("sign-in");
  const [inviteToken, setInviteToken] = useState<string | null>(null);

  useEffect(() => {
    function apply(url: string | null) {
      const token = parseInviteUrl(url);
      if (token) {
        setInviteToken(token);
        setScreen("invite");
      }
    }

    void Linking.getInitialURL().then(apply);
    const sub = Linking.addEventListener("url", (event: { url: string }) => apply(event.url));
    return () => sub.remove();
  }, []);

  if (screen === "invite") {
    return (
      <View style={styles.container} testID="mobile-driver-invite">
        <Text style={styles.title}>Driver invite</Text>
        <Text style={[styles.subtitle, styles.driverAccent]}>Complete setup in app</Text>
        <Text style={styles.token} testID="invite-token">
          Token: {inviteToken ?? "—"}
        </Text>
        <Pressable
          accessibilityRole="button"
          style={styles.button}
          testID="accept-invite-dev"
          onPress={() => setScreen("route")}
        >
          <Text style={styles.buttonText}>Continue setup (dev)</Text>
        </Pressable>
        <StatusBar style="auto" />
      </View>
    );
  }

  if (screen === "sign-in") {
    return (
      <View style={styles.container} testID="mobile-sign-in">
        <Text style={styles.title}>Sign in</Text>
        <Text style={[styles.subtitle, styles.driverAccent]}>Porterchain Driver</Text>
        <Pressable
          accessibilityRole="button"
          style={styles.button}
          testID="dev-sign-in"
          onPress={() => setScreen("route")}
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
  token: {
    ...typography.caption,
    color: colors.secondary,
    textAlign: "center",
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
