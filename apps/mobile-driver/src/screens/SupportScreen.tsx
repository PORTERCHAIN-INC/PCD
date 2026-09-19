import { useCallback, useEffect, useState } from "react";
import { ScrollView, Text, TextInput, View, StyleSheet } from "react-native";
import { colors, radius, spacing, typography } from "@porterchain/mobile-theme";
import {
  createSupportTicket,
  fetchSupportHub,
  openClaim,
  reportIncident,
  updateEmergencyContact,
} from "../api";
import { Card, CardTitle } from "../ui/Card";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";
import type { SupportHub } from "../types";

type Props = {
  onBack: () => void;
};

export function SupportScreen({ onBack }: Props) {
  const [hub, setHub] = useState<SupportHub | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [claimOrderId, setClaimOrderId] = useState("");
  const [claimType, setClaimType] = useState("damage");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [contactRel, setContactRel] = useState("");

  const reload = useCallback(() => {
    void fetchSupportHub()
      .then((next) => {
        setHub(next);
        setContactName(next.emergency_contact?.name ?? "");
        setContactPhone(next.emergency_contact?.phone ?? "");
        setContactRel(next.emergency_contact?.relationship ?? "");
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "support_failed");
      });
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const run = async (work: () => Promise<unknown>, ok: string) => {
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      await work();
      setMsg(ok);
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "action_failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen testID="mobile-support">
      <PrimaryButton tone="ghost" label="Back" onPress={onBack} />
      <Text style={styles.title}>Support</Text>
      <Text style={styles.lede}>Tickets, claims, emergency contact, and field help.</Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {msg ? <Text style={styles.ok}>{msg}</Text> : null}
      <ScrollView contentContainerStyle={styles.list} showsVerticalScrollIndicator={false}>
        <Card>
          <CardTitle>Open a ticket</CardTitle>
          <TextInput
            style={styles.input}
            value={subject}
            onChangeText={setSubject}
            placeholder="Subject"
            placeholderTextColor={colors.muted}
            editable={!busy}
          />
          <TextInput
            style={[styles.input, styles.area]}
            value={description}
            onChangeText={setDescription}
            placeholder="What happened?"
            placeholderTextColor={colors.muted}
            multiline
            editable={!busy}
          />
          <PrimaryButton
            label={busy ? "Sending…" : "Submit ticket"}
            disabled={busy || !subject.trim()}
            onPress={() =>
              void run(
                () =>
                  createSupportTicket({
                    subject: subject.trim(),
                    description: description.trim() || undefined,
                  }).then(() => {
                    setSubject("");
                    setDescription("");
                  }),
                "Ticket opened"
              )
            }
          />
        </Card>

        <Card>
          <CardTitle>Open a claim</CardTitle>
          <TextInput
            style={styles.input}
            value={claimOrderId}
            onChangeText={setClaimOrderId}
            placeholder="Order id"
            placeholderTextColor={colors.muted}
            editable={!busy}
          />
          <TextInput
            style={styles.input}
            value={claimType}
            onChangeText={setClaimType}
            placeholder="Claim type (damage, missing…)"
            placeholderTextColor={colors.muted}
            editable={!busy}
          />
          <PrimaryButton
            tone="ghost"
            label="Submit claim"
            disabled={busy || !claimOrderId.trim()}
            onPress={() =>
              void run(
                () =>
                  openClaim({
                    order_id: claimOrderId.trim(),
                    claim_type: claimType.trim() || "damage",
                    description: description.trim() || undefined,
                  }),
                "Claim filed"
              )
            }
          />
        </Card>

        <Card>
          <CardTitle>Emergency contact</CardTitle>
          <Text style={styles.meta}>
            Ops {hub?.emergency_contact?.ops_hotline ?? "—"} ·{" "}
            {hub?.emergency_contact?.ops_email ?? "—"}
          </Text>
          <TextInput
            style={styles.input}
            value={contactName}
            onChangeText={setContactName}
            placeholder="Name"
            placeholderTextColor={colors.muted}
            editable={!busy}
          />
          <TextInput
            style={styles.input}
            value={contactPhone}
            onChangeText={setContactPhone}
            placeholder="Phone"
            placeholderTextColor={colors.muted}
            keyboardType="phone-pad"
            editable={!busy}
          />
          <TextInput
            style={styles.input}
            value={contactRel}
            onChangeText={setContactRel}
            placeholder="Relationship"
            placeholderTextColor={colors.muted}
            editable={!busy}
          />
          <PrimaryButton
            tone="ghost"
            label="Save contact"
            disabled={busy || !contactName.trim() || !contactPhone.trim()}
            onPress={() =>
              void run(
                () =>
                  updateEmergencyContact({
                    name: contactName.trim(),
                    phone: contactPhone.trim(),
                    relationship: contactRel.trim() || undefined,
                  }),
                "Contact saved"
              )
            }
          />
        </Card>

        <Card>
          <CardTitle>Your tickets</CardTitle>
          {(hub?.tickets ?? []).slice(0, 8).map((t) => (
            <Text key={t.id} style={styles.body}>
              {t.subject} · {t.status.replace(/_/g, " ")}
            </Text>
          ))}
          {!hub?.tickets?.length ? <Text style={styles.meta}>No tickets yet.</Text> : null}
        </Card>

        <Card>
          <CardTitle>Claims</CardTitle>
          {(hub?.claims ?? []).slice(0, 8).map((c) => (
            <Text key={c.id} style={styles.body}>
              {c.claim_type} · {c.status.replace(/_/g, " ")} · {c.order_id}
            </Text>
          ))}
          {!hub?.claims?.length ? <Text style={styles.meta}>No claims.</Text> : null}
        </Card>

        <Card>
          <CardTitle>Incidents</CardTitle>
          {(hub?.incidents ?? []).slice(0, 6).map((i) => (
            <Text key={i.id} style={styles.body}>
              {i.incident_type.replace(/_/g, " ")} · {i.status}
            </Text>
          ))}
          <PrimaryButton
            tone="ghost"
            label="Report vehicle issue"
            disabled={busy}
            onPress={() =>
              void run(
                () =>
                  reportIncident({
                    incident_type: "vehicle_issue",
                    description: "Reported from driver mobile",
                  }),
                "Incident logged"
              )
            }
          />
        </Card>

        <Card>
          <CardTitle>Knowledge base</CardTitle>
          {(hub?.knowledge_base?.faq ?? []).slice(0, 5).map((f) => (
            <View key={f.question} style={styles.faq}>
              <Text style={styles.body}>{f.question}</Text>
              <Text style={styles.meta}>{f.answer}</Text>
            </View>
          ))}
          {(hub?.knowledge_base?.articles ?? []).slice(0, 4).map((a) => (
            <View key={a.id} style={styles.faq}>
              <Text style={styles.body}>{a.title}</Text>
              <Text style={styles.meta}>{a.body.slice(0, 160)}</Text>
            </View>
          ))}
          {!hub?.knowledge_base?.faq?.length && !hub?.knowledge_base?.articles?.length ? (
            <Text style={styles.meta}>KB empty for this environment.</Text>
          ) : null}
        </Card>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { ...typography.title, fontSize: 28, color: colors.primary },
  lede: { ...typography.caption, color: colors.muted },
  error: { ...typography.caption, color: colors.danger },
  ok: { ...typography.caption, color: colors.secondary, fontWeight: "600" },
  list: { gap: spacing.md, paddingBottom: spacing.xl },
  body: { ...typography.body, color: colors.primary, marginBottom: spacing.xs },
  meta: { ...typography.caption, color: colors.muted },
  faq: { gap: spacing.xs, marginBottom: spacing.sm },
  input: {
    ...typography.body,
    color: colors.primary,
    borderWidth: 1,
    borderColor: `${colors.primary}22`,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    marginBottom: spacing.sm,
    backgroundColor: colors.white,
  },
  area: { minHeight: 80, textAlignVertical: "top" },
});
