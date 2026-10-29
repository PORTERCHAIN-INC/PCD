/** G21 reviewer form: email + password, no code, no CAPTCHA. Rendered only when flagged on. */
import { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { useSignIn } from "@clerk/expo/legacy";
import {
  passwordSignIn,
  reviewerErrorCopy,
  reviewerLoginEnabled,
  validateCredentials,
} from "./reviewerLogin";

export function ReviewerSignIn({ onSignedIn }: { onSignedIn: () => void }) {
  const { isLoaded, signIn, setActive } = useSignIn();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!reviewerLoginEnabled()) return null;

  async function submit() {
    const bad = validateCredentials(email, password);
    if (bad) return setError(bad);
    if (!isLoaded || !signIn || !setActive) return setError(reviewerErrorCopy("not_ready"));
    setBusy(true);
    setError(null);
    try {
      await passwordSignIn(signIn, (p) => setActive(p), email, password);
      onSignedIn();
    } catch (err) {
      setError(reviewerErrorCopy(err instanceof Error ? err.message : "failed"));
    } finally {
      setBusy(false);
    }
  }

  const input = { borderWidth: 1, borderColor: "#cbd5e1", borderRadius: 10, padding: 12 } as const;
  return (
    <View testID="reviewer-sign-in" style={{ gap: 8 }}>
      <Text style={{ fontWeight: "600" }}>Sign in with email and password</Text>
      <TextInput
        testID="reviewer-email"
        style={input}
        autoCapitalize="none"
        autoComplete="email"
        keyboardType="email-address"
        placeholder="Email"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        testID="reviewer-password"
        style={input}
        secureTextEntry
        autoComplete="password"
        placeholder="Password"
        value={password}
        onChangeText={setPassword}
      />
      <Pressable
        testID="reviewer-submit"
        accessibilityRole="button"
        disabled={busy}
        onPress={() => void submit()}
        style={{ backgroundColor: "#0f2742", padding: 14, borderRadius: 10, alignItems: "center" }}
      >
        <Text style={{ color: "#fff", fontWeight: "600" }}>{busy ? "Signing in…" : "Sign in"}</Text>
      </Pressable>
      {error ? (
        <Text testID="reviewer-error" accessibilityRole="alert" style={{ color: "#b91c1c" }}>
          {error}
        </Text>
      ) : null}
    </View>
  );
}
