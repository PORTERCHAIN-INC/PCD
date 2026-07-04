import { useCallback, useState } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View } from "react-native";
import * as WebBrowser from "expo-web-browser";
import { isClerkConfigured, readMobileSecurityEnv } from "../config";

WebBrowser.maybeCompleteAuthSession();

type ClerkSignInPanelProps = {
  title: string;
  subtitle: string;
  onSignedIn: () => void | Promise<void>;
};

function isLocalDevMobile() {
  return (process.env.EXPO_PUBLIC_APP_ENV ?? "").trim() === "local";
}

export function ClerkSignInPanel({ title, subtitle, onSignedIn }: ClerkSignInPanelProps) {
  const env = readMobileSecurityEnv();
  const clerkReady = isClerkConfigured(env);

  if (!clerkReady) {
    return null;
  }

  return <ClerkSignInForm title={title} subtitle={subtitle} onSignedIn={onSignedIn} />;
}

export function DevEmailSignInPanel({
  title,
  subtitle,
  defaultEmail,
  onDevSignIn,
}: {
  title: string;
  subtitle: string;
  defaultEmail: string;
  onDevSignIn: (email: string) => Promise<void>;
}) {
  const [email, setEmail] = useState(defaultEmail);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isLocalDevMobile()) {
    return null;
  }

  const submit = async () => {
    setLoading(true);
    setError(null);
    try {
      await onDevSignIn(email);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign in failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={{ gap: 12 }}>
      <Text style={{ fontSize: 24, fontWeight: "700" }}>{title}</Text>
      <Text style={{ color: "#64748b" }}>{subtitle}</Text>
      <TextInput
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
        placeholder="Email"
        style={{
          borderWidth: 1,
          borderColor: "#e2e8f0",
          borderRadius: 12,
          paddingHorizontal: 14,
          paddingVertical: 12,
        }}
      />
      {error ? <Text style={{ color: "#dc2626" }}>{error}</Text> : null}
      <Pressable
        onPress={() => void submit()}
        disabled={loading}
        style={{
          backgroundColor: "#2563eb",
          borderRadius: 12,
          paddingVertical: 14,
          alignItems: "center",
          opacity: loading ? 0.7 : 1,
        }}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={{ color: "#fff", fontWeight: "600" }}>Continue (local dev)</Text>
        )}
      </Pressable>
    </View>
  );
}

function ClerkSignInForm({ title, subtitle, onSignedIn }: ClerkSignInPanelProps) {
  const { useSignIn, useOAuth } = require("@clerk/clerk-expo") as typeof import("@clerk/clerk-expo");
  const { signIn, setActive, isLoaded } = useSignIn();
  const google = useOAuth({ strategy: "oauth_google" });
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const finishSession = useCallback(
    async (sessionId: string) => {
      await setActive!({ session: sessionId });
      await onSignedIn();
    },
    [onSignedIn, setActive]
  );

  const onEmailSignIn = async () => {
    if (!signIn) return;
    setLoading(true);
    setError(null);
    try {
      const result = await signIn.create({ identifier: email.trim(), password });
      if (result.status === "complete" && result.createdSessionId) {
        await finishSession(result.createdSessionId);
        return;
      }
      setError("Additional verification required in Clerk.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign in failed");
    } finally {
      setLoading(false);
    }
  };

  const onGoogleSignIn = async () => {
    setLoading(true);
    setError(null);
    try {
      const { createdSessionId, setActive: oauthSetActive } = await google.startOAuthFlow();
      if (createdSessionId) {
        await oauthSetActive!({ session: createdSessionId });
        await onSignedIn();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Google sign in failed");
    } finally {
      setLoading(false);
    }
  };

  if (!isLoaded) {
    return <ActivityIndicator />;
  }

  return (
    <View style={{ gap: 12 }}>
      <Text style={{ fontSize: 24, fontWeight: "700" }}>{title}</Text>
      <Text style={{ color: "#64748b" }}>{subtitle}</Text>
      <TextInput
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
        placeholder="Email"
        style={{
          borderWidth: 1,
          borderColor: "#e2e8f0",
          borderRadius: 12,
          paddingHorizontal: 14,
          paddingVertical: 12,
        }}
      />
      <TextInput
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        placeholder="Password"
        style={{
          borderWidth: 1,
          borderColor: "#e2e8f0",
          borderRadius: 12,
          paddingHorizontal: 14,
          paddingVertical: 12,
        }}
      />
      {error ? <Text style={{ color: "#dc2626" }}>{error}</Text> : null}
      <Pressable
        onPress={() => void onEmailSignIn()}
        disabled={loading || !email || !password}
        style={{
          backgroundColor: "#2563eb",
          borderRadius: 12,
          paddingVertical: 14,
          alignItems: "center",
          opacity: loading ? 0.7 : 1,
        }}
      >
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={{ color: "#fff", fontWeight: "600" }}>Sign in</Text>}
      </Pressable>
      <Pressable
        onPress={() => void onGoogleSignIn()}
        disabled={loading}
        style={{
          borderWidth: 1,
          borderColor: "#e2e8f0",
          borderRadius: 12,
          paddingVertical: 14,
          alignItems: "center",
        }}
      >
        <Text style={{ fontWeight: "600" }}>Continue with Google</Text>
      </Pressable>
    </View>
  );
}
