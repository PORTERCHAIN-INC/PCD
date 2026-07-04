import { useState } from "react";
import { ScrollView } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import {
  authenticateWithBiometrics,
  canUseBiometrics,
  hasPin,
  useMobileSecurity,
} from "@porterchain/mobile-security";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Input, ListItem, ListSection, Screen } from "@porterchain/mobile-ui";
import { useDriverApi } from "../../api/DriverApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import { registerDriverPush } from "../../services/push";
import type { MoreStackParamList } from "../../navigation/types";

export function SettingsScreen() {
  const { theme, toggleScheme } = useTheme();
  const api = useDriverApi();
  const navigation = useNavigation<NativeStackNavigationProp<MoreStackParamList>>();
  const { biometricEnabled, pinEnabled, enableBiometric, enablePin, integrity, policy } =
    useMobileSecurity();
  const [pinDraft, setPinDraft] = useState("");

  return (
    <Screen>
      <ScreenHeader title="Settings" />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.lg }}>
        <ListSection title="App">
          <ListItem title="Dark mode" subtitle="Toggle theme" onPress={toggleScheme} />
          <ListItem
            title="Register push"
            subtitle="Firebase Cloud Messaging"
            onPress={() => void registerDriverPush(api)}
          />
          <ListItem
            title="Offline sync center"
            subtitle="Queue, uploads, GPS buffer"
            onPress={() => navigation.navigate("OfflineSync")}
          />
        </ListSection>

        <ListSection title="Security">
          <ListItem
            title="Biometric login"
            subtitle={biometricEnabled ? "Enabled" : "Disabled"}
            onPress={() => {
              void (async () => {
                if (!(await canUseBiometrics())) return;
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
            <Body muted>
              Session timeout: {policy.sessionTimeoutMinutes} minutes idle. Refresh tokens rotate
              via API.
            </Body>
          )}
        </ListSection>

        <Body muted>
          All logistics sync through Porterchain API → Fleetbase adapter (masterrule.md).
        </Body>
        <Button
          label="Open sync center"
          variant="secondary"
          fullWidth
          onPress={() => navigation.navigate("OfflineSync")}
        />
      </ScrollView>
    </Screen>
  );
}
