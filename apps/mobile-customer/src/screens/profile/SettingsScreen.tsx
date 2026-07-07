import { useState } from "react";
import { ScrollView, View } from "react-native";
import {
  authenticateWithBiometrics,
  canUseBiometrics,
  emitSecurityEvent,
  hasPin,
  useMobileSecurity,
} from "@porterchain/mobile-security";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Input, ListItem, ListSection, Screen } from "@porterchain/mobile-ui";
import { ScreenHeader } from "../../components/ScreenHeader";
import { registerCustomerPush } from "../../services/push";
import { useSettingsStore } from "../../store/settings-store";
import { useCustomerApi } from "../../api/CustomerApiContext";

export function SettingsScreen() {
  const { theme, setScheme, toggleScheme } = useTheme();
  const api = useCustomerApi();
  const themePreference = useSettingsStore((s) => s.themePreference);
  const setThemePreference = useSettingsStore((s) => s.setThemePreference);
  const { biometricEnabled, pinEnabled, enableBiometric, enablePin, integrity, policy } =
    useMobileSecurity();
  const [pinDraft, setPinDraft] = useState("");

  return (
    <Screen>
      <ScreenHeader title="Settings" subtitle="App preferences" />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.lg }}>
        <ListSection title="Appearance">
          <ListItem
            title="Dark mode"
            subtitle={themePreference === "system" ? "System" : themePreference}
            onPress={() => {
              const next = themePreference === "dark" ? "light" : "dark";
              setThemePreference(next);
              setScheme(next);
            }}
          />
          <ListItem title="Toggle theme" subtitle="Quick switch" onPress={toggleScheme} />
        </ListSection>

        <ListSection title="Security">
          <ListItem
            title="Biometric login"
            subtitle={biometricEnabled ? "Enabled" : "Disabled"}
            onPress={() => {
              void (async () => {
                const supported = await canUseBiometrics();
                if (!supported) return;
                if (!biometricEnabled) {
                  const ok = await authenticateWithBiometrics("Enable biometric unlock");
                  if (ok) await enableBiometric(true);
                } else {
                  await enableBiometric(false);
                }
              })();
            }}
          />
          <ListItem
            title="PIN lock"
            subtitle={pinEnabled ? "Enabled" : "Disabled"}
            onPress={() => {
              void (async () => {
                if (await hasPin()) {
                  await enablePin(null);
                  setPinDraft("");
                }
              })();
            }}
          />
          <Input
            label={`Set ${policy.pinLength}-digit PIN`}
            value={pinDraft}
            onChangeText={setPinDraft}
            keyboardType="number-pad"
            secureTextEntry
            maxLength={policy.pinLength}
          />
          <Button
            label="Save PIN"
            variant="secondary"
            onPress={() => {
              if (pinDraft.length === policy.pinLength) void enablePin(pinDraft);
            }}
          />
          {integrity?.compromised ? (
            <Body muted>Device integrity warning: {integrity.reasons.join(", ")}</Body>
          ) : (
            <Body muted>Session timeout: {policy.sessionTimeoutMinutes} minutes idle.</Body>
          )}
        </ListSection>

        <ListSection title="Notifications">
          <ListItem
            title="Register push device"
            subtitle="Firebase Cloud Messaging"
            onPress={() => void registerCustomerPush(api)}
          />
        </ListSection>

        <View>
          <Body muted>
            Tokens are stored in Secure Store. Audit events sync through Porterchain API.
          </Body>
        </View>
        <Button
          label="Use system theme"
          variant="ghost"
          onPress={() => {
            setThemePreference("system");
            setScheme("system");
          }}
        />
      </ScrollView>
    </Screen>
  );
}
