/** Help: call/email dispatch, open a ticket inline, see your tickets. */
import { useState } from "react";
import { Linking, StyleSheet, Text, View } from "react-native";
import { dispatchEmail, dispatchPhone } from "../config";
import { useCreateTicket, useSupportHub, useTickets } from "../data/queries";
import { haptic } from "../haptics";
import { Button } from "../ui/kit";
import { InputRow, Row, Section } from "../ui/settings/rows";
import { Sheet } from "../ui/Sheet";
import { color, space } from "../ui/theme";
import { toast } from "../ui/toast";

export function HelpPage({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  return (
    <Sheet
      visible={visible}
      title="Help"
      kicker="Dispatch · tickets"
      onClose={onClose}
      testID="page-help"
    >
      <HelpBody />
    </Sheet>
  );
}

export function HelpBody() {
  const hub = useSupportHub();
  const tickets = useTickets();
  const create = useCreateTicket();
  const [subject, setSubject] = useState("");
  const [detail, setDetail] = useState("");
  const phone = hub.data?.emergency_contact?.ops_hotline ?? dispatchPhone;
  const email = hub.data?.emergency_contact?.ops_email ?? dispatchEmail;
  const send = () =>
    create.mutate(
      { subject: subject.trim(), description: detail.trim() || undefined },
      {
        onSuccess: () => {
          haptic.success();
          setSubject("");
          setDetail("");
          toast.show("success", "Ticket sent", "Dispatch will reply here and by email.");
        },
        onError: () => toast.show("danger", "Not sent", "Try again with signal, or call dispatch."),
      }
    );
  return (
    <View style={st.wrap}>
      <Section title="TALK TO DISPATCH">
        {phone ? (
          <Row
            label="Call dispatch"
            value={phone}
            tone="accent"
            onPress={() => void Linking.openURL(`tel:${phone}`)}
          />
        ) : null}
        <Row
          label="Email dispatch"
          value={email}
          onPress={() => void Linking.openURL(`mailto:${email}`)}
        />
      </Section>
      <Section title="NEW TICKET" testID="help-new">
        <InputRow
          label="WHAT'S WRONG"
          value={subject}
          onChange={setSubject}
          placeholder="e.g. Pay for Oct 12 is missing"
        />
        <InputRow label="DETAILS (OPTIONAL)" value={detail} onChange={setDetail} multiline />
        <View style={st.pad}>
          <Button
            tone="primary"
            label="Send ticket"
            busy={create.isPending}
            disabled={subject.trim().length < 4}
            onPress={send}
          />
        </View>
      </Section>
      <Section title="MY TICKETS" testID="help-tickets">
        {(tickets.data?.tickets ?? []).slice(0, 20).map((t) => (
          <Row
            key={t.id}
            label={t.subject}
            sub={t.ticket_number ?? undefined}
            value={t.status.replace(/_/g, " ")}
          />
        ))}
        {tickets.data && !tickets.data.tickets.length ? <Row label="No tickets" /> : null}
        {!tickets.data ? <Row label="Loading…" /> : null}
      </Section>
      <Text style={st.muted}>In danger? Use SOS on the Me tab or call 911.</Text>
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { gap: space.lg },
  pad: { padding: space.lg },
  muted: { fontSize: 14, color: color.inkMuted },
});
