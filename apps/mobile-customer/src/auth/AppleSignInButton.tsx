/**
 * Sign in with Apple via Keycloak (L36, Guideline 4.8). Placeholder: hidden until
 * EXPO_PUBLIC_APPLE_SIGN_IN_ENABLED=true and Keycloak env is set. Same size as Google (A-APR-04).
 * Code exchange + session handoff land with the Keycloak migration (week 1–2 L36 work).
 */
import { Pressable, Text } from "react-native";
import * as WebBrowser from "expo-web-browser";
import { appleAuthorizeUrl, appleSignInEnabled, keycloakConfig } from "./reviewerLogin";

export function AppleSignInButton({ redirectUri }: { redirectUri: string }) {
  const kc = keycloakConfig();
  if (!appleSignInEnabled() || !kc) return null;
  return (
    <Pressable
      testID="apple-sign-in"
      accessibilityRole="button"
      accessibilityLabel="Sign in with Apple"
      onPress={() =>
        void WebBrowser.openAuthSessionAsync(
          appleAuthorizeUrl(kc, redirectUri, String(Date.now())),
          redirectUri
        )
      }
      style={{ backgroundColor: "#000", padding: 14, borderRadius: 10, alignItems: "center" }}
    >
      <Text style={{ color: "#fff", fontWeight: "600" }}>{"\uF8FF"} Sign in with Apple</Text>
    </Pressable>
  );
}
