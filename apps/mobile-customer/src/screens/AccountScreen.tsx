import { useClerk } from "@clerk/expo";
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Pressable,
  ScrollView,
  Share,
  Text,
  TextInput,
  View,
  StyleSheet,
} from "react-native";
import { colors, radius, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";
import {
  createSupport,
  fetchOnboarding,
  listSupport,
  privacyDeleteRequest,
  privacyExport,
  type OnboardingStatus,
  type SupportTicket,
} from "../api";
import { humanCustomerError } from "../errors";
import { sessionIdentity } from "../session";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";

export function AccountScreen({ onSignedOut }: { onSignedOut: () => void }) {
  const identity = sessionIdentity();
  const clerk = useClerk();
  const [onboarding, setOnboarding] = useState<OnboardingStatus | null>(null);
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    void Promise.all([fetchOnboarding(), listSupport()])
      .then(([status, rows]) => {
        setOnboarding(status);
        setTickets(rows);
      })
      .catch((err: unknown) => {
        setError(humanCustomerError(err instanceof Error ? err.message : "request_failed"));
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function submitTicket() {
    if (!subject.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createSupport({
        subject: subject.trim(),
        description: description.trim() || undefined,
      });
      setSubject("");
      setDescription("");
      setMessage("Support request submitted.");
      load();
    } catch (err) {
      setError(humanCustomerError(err instanceof Error ? err.message : "request_failed"));
    } finally {
      setBusy(false);
    }
  }

  async function exportData() {
    setBusy(true);
    setError(null);
    try {
      const data = await privacyExport();
      await Share.share({ message: JSON.stringify(data, null, 2) });
      setMessage("Privacy export ready to share.");
    } catch (err) {
      setError(humanCustomerError(err instanceof Error ? err.message : "request_failed"));
    } finally {
      setBusy(false);
    }
  }

  function requestDelete() {
    Alert.alert(
      "Request deletion",
      "This opens a hold for review. Booking stops while the hold is open.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Request deletion",
          style: "destructive",
          onPress: () => {
            setBusy(true);
            void privacyDeleteRequest()
              .then((res) => setMessage(`${res.message} Reference: ${res.reference}`))
              .catch((err: unknown) => {
                setError(humanCustomerError(err instanceof Error ? err.message : "request_failed"));
              })
              .finally(() => setBusy(false));
          },
        },
      ]
    );
  }

  function signOut() {
    Alert.alert("Sign out of Porterchain on this device?", undefined, [
      { text: "Cancel", style: "cancel" },
      { text: "Sign out", style: "destructive", onPress: onSignedOut },
    ]);
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>Account</Text>
        <View style={styles.profile}>
          <Text style={styles.strong}>{identity.email || "Customer"}</Text>
          <Text style={styles.meta}>
            {onboarding?.ready ? "Portal ready" : "Onboarding still has open steps"}
          </Text>
        </View>
        {message ? <Text style={styles.meta}>{message}</Text> : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <Text style={styles.section}>Report a problem</Text>
        <TextInput
          style={styles.input}
          placeholder="Subject"
          value={subject}
          onChangeText={setSubject}
          placeholderTextColor={colors.muted}
        />
        <TextInput
          style={styles.input}
          placeholder="Details"
          value={description}
          onChangeText={setDescription}
          placeholderTextColor={colors.muted}
        />
        <PrimaryButton
          label={busy ? "Working…" : "Submit ticket"}
          disabled={busy}
          onPress={() => void submitTicket()}
        />
        {tickets.map((ticket) => (
          <Text key={ticket.ticket_id} style={styles.meta}>
            {ticket.subject} · {ticket.status}
          </Text>
        ))}
        <Text style={styles.section}>Security</Text>
        <PrimaryButton
          label="Password and security"
          onPress={() => {
            const open = (clerk as { openUserProfile?: () => void }).openUserProfile;
            if (open) open();
            else {
              Alert.alert(
                "Password",
                "Use Forgot password on the sign-in screen. Porterchain does not store your password."
              );
            }
          }}
        />
        <Text style={styles.section}>Privacy</Text>
        <PrimaryButton label="Export my data" disabled={busy} onPress={() => void exportData()} />
        <Pressable onPress={requestDelete}>
          <Text style={styles.danger}>Request deletion</Text>
        </Pressable>
        <Pressable onPress={signOut}>
          <Text style={styles.danger}>Sign out</Text>
        </Pressable>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: { gap: 10, paddingBottom: 32 },
  title: { ...typography.title, fontSize: 30, color: colors.primary },
  profile: { backgroundColor: colors.white, borderRadius: radius.xl, padding: 16, gap: 4 },
  strong: { ...typography.body, color: colors.primary, fontWeight: "700" },
  section: {
    ...typography.caption,
    color: colors.muted,
    textTransform: "uppercase",
    letterSpacing: 1,
    marginTop: 8,
  },
  meta: { ...typography.caption, color: colors.muted },
  error: { ...typography.caption, color: colors.danger },
  danger: { ...typography.caption, color: colors.danger, textAlign: "center", paddingVertical: 8 },
  input: {
    minHeight: touchTargetMin,
    borderWidth: 1,
    borderColor: `${colors.primary}26`,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.md,
    backgroundColor: colors.white,
    color: colors.primary,
  },
});
