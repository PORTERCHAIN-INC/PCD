import { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView } from "react-native";
import {
  ClerkSignInPanel,
  DevEmailSignInPanel,
  emitSecurityEvent,
  getClerkBearerToken,
  getClerkPrimaryEmail,
  type ClerkSignInContext,
} from "@porterchain/mobile-security";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Screen } from "@porterchain/mobile-ui";
import { ApiError } from "@porterchain/mobile-api";
import { useDriverApi } from "../../api/DriverApiContext";
import { mobileEnv, isClerkConfigured } from "../../config/env";
import { useAuthStore } from "../../store/auth-store";

function formatSignInError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.message === "driver_not_found") {
      return "No driver account for this email. Ask ops to invite you as a driver first.";
    }
    if (error.message === "driver_not_active") {
      return "Your driver account is not active yet.";
    }
    if (error.message === "email_clerk_mismatch") {
      return "Email does not match your Clerk sign-in. Use the email on your driver invite.";
    }
    if (error.message === "driver_clerk_mismatch") {
      return "This Clerk account is linked to a different driver profile.";
    }
    if (error.message === "invalid_token" || error.message === "clerk_token_required") {
      return "Clerk sign-in could not be verified. Restart the app and try again.";
    }
    if (error.status >= 500) {
      return "Server error during sign-in. Try again shortly or contact support.";
    }
    return error.message;
  }
  if (error instanceof Error) {
    if (error.message === "email_required") {
      return "Clerk did not return an email. Add an email to your Clerk account.";
    }
    return error.message;
  }
  return "Sign in failed";
}

export function SignInScreen() {
  const { theme } = useTheme();
  const api = useDriverApi();
  const setSession = useAuthStore((s) => s.setSession);
  const clerkConfigured = isClerkConfigured();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const showDevPanel = !clerkConfigured && (process.env.EXPO_PUBLIC_APP_ENV ?? "").trim() === "local";

  async function completeDriverSession(ctx: ClerkSignInContext) {
    const clerkToken = ctx.clerkToken ?? (await getClerkBearerToken());
    if (!clerkToken) {
      throw new Error("Clerk session missing — sign in again.");
    }
    const email = ctx.email ?? getClerkPrimaryEmail();
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
        <ScrollView
          contentContainerStyle={{ padding: theme.spacing["2xl"], gap: theme.spacing.lg }}
        >
          {clerkConfigured ? (
            <ClerkSignInPanel
              title="Porterchain Driver"
              subtitle="Execute routes, capture POD, earn on every delivery."
              onSignedIn={async (ctx) => {
                setLoading(true);
                setError(null);
                try {
                  await completeDriverSession(ctx);
                } catch (e) {
                  setError(formatSignInError(e));
                } finally {
                  setLoading(false);
                }
              }}
            />
          ) : showDevPanel ? (
            <DevEmailSignInPanel
              title="Porterchain Driver"
              subtitle="Local dev — email only when API has CLERK_DEV_BYPASS=true and APP_ENV=local."
              defaultEmail="marco@porterchain.com"
              onDevSignIn={devSignIn}
            />
          ) : (
            <Body style={{ color: theme.colors.textMuted }}>
              Sign-in is not configured. Set EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY in apps/mobile-driver/.env,
              restart Metro, then rebuild from Xcode.
            </Body>
          )}
          {error ? <Body style={{ color: theme.colors.danger }}>{error}</Body> : null}
          {loading ? <Body muted>Signing in…</Body> : null}
        </ScrollView>
      </KeyboardAvoidingView>
    </Screen>
  );
}
