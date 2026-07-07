"use client";

import { Switch, View } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Caption, ListItem, ListSection, Screen } from "@porterchain/mobile-ui";
import { useNotificationPreferences } from "../hooks/useNotificationPreferences";
import { useNotificationContext } from "../provider/NotificationProvider";
import type { NotificationPreference } from "../types";

function labelForCategory(category: string) {
  return category.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export function NotificationSettingsScreen() {
  const { theme } = useTheme();
  const { adapter } = useNotificationContext();
  const { preferences, isLoading, isSaving, update, enabled } = useNotificationPreferences(adapter);

  if (!enabled) {
    return (
      <Screen>
        <View style={{ padding: theme.spacing.lg }}>
          <Body muted>Notification preferences are not available for this account yet.</Body>
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={{ padding: theme.spacing.lg, gap: theme.spacing.xs }}>
        <Body style={{ fontSize: 24, fontWeight: "700" }}>Notification settings</Body>
        <Caption>
          Managed by Porterchain Notification Engine. Push delivery respects these preferences.
        </Caption>
      </View>
      <ListSection title="Categories">
        {isLoading ? (
          <Body muted style={{ padding: theme.spacing.lg }}>
            Loading preferences…
          </Body>
        ) : null}
        {preferences.map((pref: NotificationPreference) => (
          <View
            key={pref.category}
            style={{ backgroundColor: theme.colors.surface, marginBottom: theme.spacing.sm }}
          >
            <ListItem
              title={labelForCategory(pref.category)}
              subtitle="In-app"
              trailing={
                <Switch
                  value={pref.in_app_enabled}
                  disabled={isSaving === pref.category}
                  onValueChange={(value) =>
                    void update({ category: pref.category, in_app_enabled: value })
                  }
                />
              }
              showDivider
            />
            <ListItem
              title="Push"
              trailing={
                <Switch
                  value={pref.push_enabled}
                  disabled={isSaving === pref.category}
                  onValueChange={(value) =>
                    void update({ category: pref.category, push_enabled: value })
                  }
                />
              }
              showDivider
            />
            <ListItem
              title="Email"
              trailing={
                <Switch
                  value={pref.email_enabled}
                  disabled={isSaving === pref.category}
                  onValueChange={(value) =>
                    void update({ category: pref.category, email_enabled: value })
                  }
                />
              }
              showDivider={false}
            />
          </View>
        ))}
      </ListSection>
    </Screen>
  );
}
