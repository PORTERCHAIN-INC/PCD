import { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView } from "react-native";
import {
  ClerkSignInPanel,
  DevEmailSignInPanel,
  emitSecurityEvent,
  getClerkBearerToken,
  getClerkPrimaryEmail,
  isClerkConfigured,
  readMobileSecurityEnv,
} from "@porterchain/mobile-security";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Screen } from "@porterchain/mobile-ui";
import { useDriverApi } from "../../api/DriverApiContext";
import { useAuthStore } from "../../store/auth-store";

export function SignInScreen() {
  const { theme } = useTheme();
  const api = useDriverApi();
  const setSession = useAuthStore((s) => s.setSession);
  const env = readMobileSecurityEnv();
  const clerkConfigured = isClerkConfigured(env);
  const [error, setError] = useState<string | null>(null);

  async function completeDriverSession() {
    const clerkToken = await getClerkBearerToken();
    if (!clerkToken) {
      throw new Error("Clerk session missing — sign in again.");
    }
    const email = getClerkPrimaryEmail();
    if (!email) {
      throw new Error("email_required");
    }
    const tokens = await api.login(email, clerkToken);
    await setSession({
      token: tokens.access_token,
      refreshToken: tokens.refresh_token,
      driverId: tokens.driver_id,
      email,
    });
    await emitSecurityEvent("login_success", { app: "driver" });
  }

  async function devSignIn(email: string) {
    const tokens = await api.login(email, "dev");
    await setSession({
      token: tokens.access_token,
      refreshToken: tokens.refresh_token,
      driverId: tokens.driver_id,
      email,
    });
    await emitSecurityEvent("login_success", { app: "driver", mode: "dev" });
  }

  return (
    <Screen style={{ justifyContent: "center" }}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={{ padding: theme.spacing["2xl"], gap: theme.spacing.lg }}>
          {clerkConfigured ? (
            <ClerkSignInPanel
              title="Porterchain Driver"
              subtitle="Execute routes, capture POD, earn on every delivery."
              onSignedIn={async () => {
                try {
                  await completeDriverSession();
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Sign in failed");
                }
              }}
            />
          ) : (
            <DevEmailSignInPanel
              title="Porterchain Driver"
              subtitle="Local dev — email only when API has CLERK_DEV_BYPASS=true and APP_ENV=local."
              defaultEmail="marco@porterchain.com"
              onDevSignIn={devSignIn}
            />
          )}
          {error ? <Body style={{ color: theme.colors.danger }}>{error}</Body> : null}
        </ScrollView>
      </KeyboardAvoidingView>
    </Screen>
  );
}
