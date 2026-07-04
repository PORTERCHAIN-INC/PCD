import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { View } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Caption } from "@porterchain/mobile-ui";
import { AppShell } from "../components/AppShell";
import type { MainTabParamList } from "./types";
import { HomeStack } from "./stacks/HomeStack";
import { JobsStack } from "./stacks/JobsStack";
import { NavigationStack } from "./stacks/NavigationStack";
import { EarningsStack } from "./stacks/EarningsStack";
import { ShiftStack } from "./stacks/ShiftStack";
import { MoreStack } from "./stacks/MoreStack";

const Tab = createBottomTabNavigator<MainTabParamList>();

function TabIcon({ label, focused }: { label: string; focused: boolean }) {
  const { theme } = useTheme();
  return (
    <View style={{ alignItems: "center", minWidth: 48 }}>
      <View style={{ width: 6, height: 6, borderRadius: 3, marginBottom: 4, backgroundColor: focused ? theme.colors.secondary : "transparent" }} />
      <Caption style={{ color: focused ? theme.colors.secondary : theme.colors.textMuted, fontWeight: focused ? "700" : "500", fontSize: 10 }}>
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
        <Tab.Screen name="Home" component={HomeStack} options={{ tabBarIcon: ({ focused }) => <TabIcon label="Home" focused={focused} /> }} />
        <Tab.Screen name="Jobs" component={JobsStack} options={{ tabBarIcon: ({ focused }) => <TabIcon label="Jobs" focused={focused} /> }} />
        <Tab.Screen name="Navigation" component={NavigationStack} options={{ tabBarIcon: ({ focused }) => <TabIcon label="Nav" focused={focused} /> }} />
        <Tab.Screen name="Earnings" component={EarningsStack} options={{ tabBarIcon: ({ focused }) => <TabIcon label="Earn" focused={focused} /> }} />
        <Tab.Screen name="Shift" component={ShiftStack} options={{ tabBarIcon: ({ focused }) => <TabIcon label="Shift" focused={focused} /> }} />
        <Tab.Screen name="More" component={MoreStack} options={{ tabBarIcon: ({ focused }) => <TabIcon label="More" focused={focused} /> }} />
      </Tab.Navigator>
    </AppShell>
  );
}
