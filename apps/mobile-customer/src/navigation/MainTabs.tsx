import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { useTheme } from "@porterchain/mobile-theme";
import { Caption } from "@porterchain/mobile-ui";
import { View } from "react-native";
import type { MainTabParamList } from "./types";
import { HomeStack } from "./stacks/HomeStack";
import { BookingsStack } from "./stacks/BookingsStack";
import { TrackingStack } from "./stacks/TrackingStack";
import { NotificationsStack } from "./stacks/NotificationsStack";
import { ProfileStack } from "./stacks/ProfileStack";
import { AppShell } from "../components/AppShell";

const Tab = createBottomTabNavigator<MainTabParamList>();

function TabIcon({ label, focused }: { label: string; focused: boolean }) {
  const { theme } = useTheme();
  return (
    <View style={{ alignItems: "center", justifyContent: "center", minWidth: 56 }}>
      <View
        style={{
          width: 6,
          height: 6,
          borderRadius: 3,
          marginBottom: 4,
          backgroundColor: focused ? theme.colors.secondary : "transparent",
        }}
      />
      <Caption style={{ color: focused ? theme.colors.secondary : theme.colors.textMuted, fontWeight: focused ? "700" : "500" }}>
        {label}
      </Caption>
    </View>
  );
}

export function MainTabs() {
  const { theme } = useTheme();

  return (
    <AppShell>
      <Tab.Navigator
        screenOptions={{
          headerShown: false,
          tabBarStyle: {
            backgroundColor: theme.colors.surface,
            borderTopColor: theme.colors.border,
            height: theme.layout.tabBarHeight,
            paddingTop: theme.spacing.xs,
          },
          tabBarShowLabel: false,
        }}
      >
        <Tab.Screen
          name="Home"
          component={HomeStack}
          options={{ tabBarIcon: ({ focused }) => <TabIcon label="Home" focused={focused} /> }}
        />
        <Tab.Screen
          name="Bookings"
          component={BookingsStack}
          options={{ tabBarIcon: ({ focused }) => <TabIcon label="Bookings" focused={focused} /> }}
        />
        <Tab.Screen
          name="Tracking"
          component={TrackingStack}
          options={{ tabBarIcon: ({ focused }) => <TabIcon label="Tracking" focused={focused} /> }}
        />
        <Tab.Screen
          name="Notifications"
          component={NotificationsStack}
          options={{ tabBarIcon: ({ focused }) => <TabIcon label="Alerts" focused={focused} /> }}
        />
        <Tab.Screen
          name="Profile"
          component={ProfileStack}
          options={{ tabBarIcon: ({ focused }) => <TabIcon label="Profile" focused={focused} /> }}
        />
      </Tab.Navigator>
    </AppShell>
  );
}
