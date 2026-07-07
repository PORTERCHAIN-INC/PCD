import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View } from "react-native";
import * as WebBrowser from "expo-web-browser";
import { isClerkConfigured, readMobileSecurityEnv } from "../config";

WebBrowser.maybeCompleteAuthSession();

export type ClerkSignInContext = {
  clerkToken: string;
  email?: string;
};

type ClerkSignInPanelProps = {
  title: string;
  subtitle: string;
  onSignedIn: (ctx: ClerkSignInContext) => void | Promise<void>;
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

function isSessionAlreadyExistsError(error: unknown): boolean {
  const message =
    error instanceof Error ? error.message.toLowerCase() : String(error).toLowerCase();
  if (message.includes("already signed in") || message.includes("session_exists")) {
    return true;
  }
  const clerkErrors = (error as { errors?: Array<{ code?: string; message?: string }> })?.errors;
  if (Array.isArray(clerkErrors)) {
    return clerkErrors.some(
      (e) =>
        e.code === "session_exists" || (e.message ?? "").toLowerCase().includes("already signed in")
    );
  }
  return false;
}

function ClerkSignInForm({ title, subtitle, onSignedIn }: ClerkSignInPanelProps) {
  const { useSignIn, useOAuth, useAuth, useUser } =
    require("@clerk/clerk-expo") as typeof import("@clerk/clerk-expo");
  const { signIn, setActive, isLoaded } = useSignIn();
  const { getToken, isSignedIn, signOut } = useAuth();
  const { user } = useUser();
  const google = useOAuth({ strategy: "oauth_google" });
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const autoResumeAttempted = useRef(false);

  // Exchange the active Clerk session for a Porterchain session.
  const runExchange = useCallback(
    async (emailHint?: string) => {
      const clerkToken = (await getToken()) ?? null;
      if (!clerkToken) {
        throw new Error("Clerk session missing — sign in again.");
      }
      const resolvedEmail =
        emailHint?.trim() || user?.primaryEmailAddress?.emailAddress || undefined;
      await onSignedIn({ clerkToken, email: resolvedEmail });
    },
    [getToken, onSignedIn, user]
  );

  const finishSession = useCallback(
    async (sessionId: string, emailHint?: string) => {
      await setActive!({ session: sessionId });
      await runExchange(emailHint);
    },
    [runExchange, setActive]
  );

  // If a Clerk session already exists (e.g. a prior attempt created one but the
  // Porterchain exchange failed), resume it automatically instead of trapping the
  // user on "you're already signed in".
  useEffect(() => {
    if (!isLoaded || !isSignedIn || autoResumeAttempted.current) return;
    autoResumeAttempted.current = true;
    setLoading(true);
    setError(null);
    void (async () => {
      try {
        await runExchange();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Sign in failed");
      } finally {
        setLoading(false);
      }
    })();
  }, [isLoaded, isSignedIn, runExchange]);

  const onEmailSignIn = async () => {
    if (!signIn) return;
    setLoading(true);
    setError(null);
    try {
      const result = await signIn.create({ identifier: email.trim(), password });
      if (result.status === "complete" && result.createdSessionId) {
        await finishSession(result.createdSessionId, email);
        return;
      }
      setError("Additional verification required in Clerk.");
    } catch (e) {
      // A leftover Clerk session blocks a fresh sign-in — resume it instead.
      if (isSessionAlreadyExistsError(e)) {
        try {
          await runExchange(email);
          return;
        } catch (resumeError) {
          setError(resumeError instanceof Error ? resumeError.message : "Sign in failed");
          return;
        }
      }
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
        await runExchange();
      } else {
        // OAuth returned no new session — an active one may already exist.
        await runExchange();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Google sign in failed");
    } finally {
      setLoading(false);
    }
  };

  const onUseDifferentAccount = async () => {
    setLoading(true);
    setError(null);
    try {
      await signOut();
      autoResumeAttempted.current = false;
    } catch {
      // ignore — Clerk clears local session best-effort
    } finally {
      setLoading(false);
    }
  };

  if (!isLoaded) {
    return <ActivityIndicator />;
  }

  // Existing Clerk session — offer resume + escape hatch instead of re-login.
  if (isSignedIn) {
    const signedInEmail = user?.primaryEmailAddress?.emailAddress;
    return (
      <View style={{ gap: 12 }}>
        <Text style={{ fontSize: 24, fontWeight: "700" }}>{title}</Text>
        <Text style={{ color: "#64748b" }}>
          {signedInEmail ? `Signed in as ${signedInEmail}.` : "You're already signed in."}
        </Text>
        {error ? <Text style={{ color: "#dc2626" }}>{error}</Text> : null}
        <Pressable
          onPress={() => {
            autoResumeAttempted.current = false;
            setLoading(true);
            setError(null);
            void (async () => {
              try {
                await runExchange();
              } catch (e) {
                setError(e instanceof Error ? e.message : "Sign in failed");
              } finally {
                setLoading(false);
              }
            })();
          }}
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
            <Text style={{ color: "#fff", fontWeight: "600" }}>Continue</Text>
          )}
        </Pressable>
        <Pressable
          onPress={() => void onUseDifferentAccount()}
          disabled={loading}
          style={{
            borderWidth: 1,
            borderColor: "#e2e8f0",
            borderRadius: 12,
            paddingVertical: 14,
            alignItems: "center",
          }}
        >
          <Text style={{ fontWeight: "600" }}>Use a different account</Text>
        </Pressable>
      </View>
    );
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
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={{ color: "#fff", fontWeight: "600" }}>Sign in</Text>
        )}
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
