import { useClerk } from "@clerk/expo";
import { useCallback, useEffect, useState } from "react";
import { Alert, Share, StyleSheet, TextInput, View } from "react-native";
import * as WebBrowser from "expo-web-browser";
import { appVersion, websiteUrl } from "../config";
import { friendlyDate } from "../format";
import { radius, spacing, touchTargetMin, useThemed, type Palette } from "../theme";
import { Banner, Button, Card, Divider, ListRow, SectionHeader, StatusPill, Txt } from "../ui/kit";
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
  const [composing, setComposing] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const { colors: c, styles } = useThemed(makeStyles);

  const load = useCallback(() => {
    setRefreshing(true);
    void Promise.all([fetchOnboarding(), listSupport()])
      .then(([status, rows]) => {
        setOnboarding(status);
        setTickets(rows);
      })
      .catch((err: unknown) => {
        setError(humanCustomerError(err instanceof Error ? err.message : "request_failed"));
      })
      .finally(() => setRefreshing(false));
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
      setMessage("Sent. Support will reply by email.");
      setComposing(false);
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

  const initial = (identity.email || "C")[0]!.toUpperCase();

  return (
    <Screen scroll testID="account" title="Account" refreshing={refreshing} onRefresh={load}>
      <Card style={{ flexDirection: "row", alignItems: "center", gap: spacing.md }}>
        <View style={[styles.avatar, { backgroundColor: c.secondary }]}>
          <Txt v="title" tone="onAccent">
            {initial}
          </Txt>
        </View>
        <View style={{ flex: 1, gap: 2 }}>
          <Txt v="headline">{identity.email || "Customer"}</Txt>
          <StatusPill
            label={onboarding?.ready === false ? "Setup incomplete" : "Account active"}
            tone={onboarding?.ready === false ? "info" : "success"}
          />
        </View>
      </Card>
      {message ? <Banner tone="success" text={message} /> : null}
      {error ? <Banner tone="danger" text={error} /> : null}

      <SectionHeader title="Help & support" />
      <Card style={{ paddingVertical: spacing.xs, gap: 0 }}>
        <ListRow
          icon="chatbubble-ellipses-outline"
          title="Report a problem"
          subtitle="Our team replies by email"
          onPress={() => setComposing((v) => !v)}
          testID="account-support"
        />
        {composing ? (
          <View style={{ gap: spacing.sm, paddingBottom: spacing.md }}>
            <TextInput
              style={styles.input}
              accessibilityLabel="Subject"
              placeholder="What went wrong?"
              value={subject}
              onChangeText={setSubject}
              placeholderTextColor={c.muted}
              maxFontSizeMultiplier={1.6}
              returnKeyType="next"
            />
            <TextInput
              style={[styles.input, { minHeight: 96, textAlignVertical: "top", paddingTop: 12 }]}
              accessibilityLabel="Details"
              placeholder="Details, tracking number, anything that helps"
              value={description}
              onChangeText={setDescription}
              placeholderTextColor={c.muted}
              multiline
              maxFontSizeMultiplier={1.6}
            />
            <Button
              label="Send to support"
              loading={busy}
              disabled={!subject.trim()}
              onPress={() => void submitTicket()}
            />
          </View>
        ) : null}
        {tickets.map((ticket) => (
          <View key={ticket.ticket_id}>
            <Divider />
            <ListRow
              icon="mail-outline"
              title={ticket.subject}
              subtitle={friendlyDate(ticket.created_at)}
              right={
                <StatusPill
                  label={ticket.status.replace(/_/g, " ")}
                  tone={/resolved|closed/i.test(ticket.status) ? "success" : "info"}
                />
              }
            />
          </View>
        ))}
        <Divider />
        <ListRow
          icon="globe-outline"
          title="Questions & answers"
          subtitle="porterchain.com/faq"
          onPress={() => void WebBrowser.openBrowserAsync(`${websiteUrl}/en/faq`)}
        />
      </Card>

      <SectionHeader title="Security & privacy" />
      <Card style={{ paddingVertical: spacing.xs, gap: 0 }}>
        <ListRow
          icon="lock-closed-outline"
          title="Password and security"
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
        <Divider />
        <ListRow
          icon="download-outline"
          title="Export my data"
          subtitle="A copy of your PorterChain data"
          onPress={busy ? undefined : () => void exportData()}
        />
        <Divider />
        <ListRow
          icon="trash-outline"
          title="Request account deletion"
          danger
          onPress={requestDelete}
        />
      </Card>

      <Button label="Sign out" variant="danger" icon="log-out-outline" onPress={signOut} />
      <Txt v="caption" tone="muted" center>
        PorterChain {appVersion}
      </Txt>
    </Screen>
  );
}

const makeStyles = (c: Palette) =>
  StyleSheet.create({
    avatar: {
      width: 52,
      height: 52,
      borderRadius: 26,
      alignItems: "center",
      justifyContent: "center",
    },
    input: {
      minHeight: touchTargetMin + 4,
      borderWidth: 1,
      borderColor: c.border,
      borderRadius: radius.lg,
      paddingHorizontal: spacing.md,
      backgroundColor: c.grayBg,
      color: c.primary,
      fontSize: 16,
    },
  });
