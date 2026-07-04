import { useEffect } from "react";
import { ActivityIndicator, View } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { SecurityShell } from "@porterchain/mobile-security";
import { useTheme } from "@porterchain/mobile-theme";
import { useAuthStore, useIsSignedIn } from "../store/auth-store";
import { useSettingsStore } from "../store/settings-store";
import { registerCustomerPush } from "../services/push";
import { useCustomerApi } from "../api/CustomerApiContext";
import { SignInScreen } from "../screens/auth/SignInScreen";
import { navigationRef } from "./navigation-ref";
import { useAppLinking } from "./useAppLinking";
import { MainTabs } from "./MainTabs";
import type { RootStackParamList } from "./types";

const Stack = createNativeStackNavigator<RootStackParamList>();

function MainShell() {
  const api = useCustomerApi();

  useEffect(() => {
    void registerCustomerPush(api);
  }, [api]);

  return (
    <SecurityShell>
      <MainTabs />
    </SecurityShell>
  );
}

export function RootNavigator() {
  const { theme } = useTheme();
  const hydrateAuth = useAuthStore((s) => s.hydrate);
  const hydrateSettings = useSettingsStore((s) => s.hydrate);
  const { signedIn, hydrated } = useIsSignedIn();

  useAppLinking(navigationRef, signedIn);

  useEffect(() => {
    hydrateSettings();
    void hydrateAuth();
  }, [hydrateAuth, hydrateSettings]);

  if (!hydrated) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.background }}>
        <ActivityIndicator color={theme.colors.secondary} />
      </View>
    );
  }

  return (
    <NavigationContainer ref={navigationRef}>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {signedIn ? (
          <Stack.Screen name="Main" component={MainShell} />
        ) : (
          <Stack.Screen name="SignIn" component={SignInScreen} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
