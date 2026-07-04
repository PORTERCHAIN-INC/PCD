import { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, View } from "react-native";
import { createApiClient, createCustomerApi } from "@porterchain/mobile-api";
import {
  ClerkSignInPanel,
  DevEmailSignInPanel,
  emitSecurityEvent,
  getClerkBearerToken,
  isClerkConfigured,
  readMobileSecurityEnv,
} from "@porterchain/mobile-security";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Screen } from "@porterchain/mobile-ui";
import { mobileEnv } from "../../config/env";
import { useAuthStore } from "../../store/auth-store";

export function SignInScreen() {
  const { theme } = useTheme();
  const setSession = useAuthStore((s) => s.setSession);
  const env = readMobileSecurityEnv();
  const clerkConfigured = isClerkConfigured(env);
  const [error, setError] = useState<string | null>(null);

  async function completeCustomerSession(emailHint?: string) {
    const clerkToken = await getClerkBearerToken();
    if (!clerkToken) {
      throw new Error("Clerk session missing — sign in again.");
    }
    const me = await createCustomerApi(
      createApiClient({ baseUrl: mobileEnv.apiBaseUrl, getAccessToken: () => clerkToken })
    ).authMe();
    await setSession({
      token: clerkToken,
      clerkUserId: me.user_id,
      email: me.email ?? emailHint ?? "",
    });
    await emitSecurityEvent("login_success", { app: "customer" });
  }

  async function devSignIn(email: string) {
    const clerkToken = "dev";
    await setSession({ token: clerkToken, clerkUserId: "dev_clerk_user", email });
    await emitSecurityEvent("login_success", { app: "customer", mode: "dev" });
  }

  return (
    <Screen style={{ justifyContent: "center" }}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={{ padding: theme.spacing["2xl"], gap: theme.spacing.lg }}>
          {clerkConfigured ? (
            <ClerkSignInPanel
              title="Porterchain"
              subtitle="Book deliveries, track shipments, manage invoices."
              onSignedIn={() => completeCustomerSession()}
            />
          ) : (
            <DevEmailSignInPanel
              title="Porterchain"
              subtitle="Local dev — uses Porterchain dev token when API has CLERK_DEV_BYPASS=true and APP_ENV=local."
              defaultEmail="customer@porterchain.com"
              onDevSignIn={devSignIn}
            />
          )}
          {error ? <Body style={{ color: theme.colors.danger }}>{error}</Body> : null}
          {!clerkConfigured ? (
            <Body muted style={{ textAlign: "center" }}>
              Set EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY for production Clerk auth.
            </Body>
          ) : null}
        </ScrollView>
      </KeyboardAvoidingView>
    </Screen>
  );
}
