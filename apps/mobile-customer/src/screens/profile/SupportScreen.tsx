import { useState } from "react";
import { ScrollView } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CUSTOMER_OFFLINE_ACTIONS } from "@porterchain/mobile-api";
import { useOfflineSync } from "@porterchain/mobile-offline";
import { useTheme } from "@porterchain/mobile-theme";
import {
  Body,
  Button,
  Input,
  ListItem,
  ListSection,
  Screen,
  SkeletonList,
} from "@porterchain/mobile-ui";
import { useCustomerApi } from "../../api/CustomerApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";

export function SupportScreen() {
  const { theme } = useTheme();
  const api = useCustomerApi();
  const { runDirectOrQueue } = useOfflineSync();
  const queryClient = useQueryClient();

  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [orderId, setOrderId] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["customer", "support"],
    queryFn: () => api.listSupport(),
  });

  async function submit() {
    setSaving(true);
    setMessage(null);
    const payload = { subject, description, order_id: orderId || undefined };
    try {
      const result = await runDirectOrQueue(
        CUSTOMER_OFFLINE_ACTIONS.SUPPORT_CREATE,
        payload,
        async () => {
          await api.createSupport(payload);
          await queryClient.invalidateQueries({ queryKey: ["customer", "support"] });
        }
      );
      setMessage(
        result.mode === "queued" ? "Saved offline — will send when connected." : "Ticket created."
      );
      setSubject("");
      setDescription("");
      setOrderId("");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader title="Support" subtitle="We're here to help" />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.lg }}>
        <Input label="Subject" value={subject} onChangeText={setSubject} />
        <Input label="Order ID (optional)" value={orderId} onChangeText={setOrderId} />
        <Input label="Description" value={description} onChangeText={setDescription} multiline />
        {message ? <Body muted>{message}</Body> : null}
        <Button label="Submit ticket" loading={saving} fullWidth onPress={() => void submit()} />

        {isLoading ? <SkeletonList /> : null}
        <ListSection title="Your tickets">
          {(data ?? []).map((ticket) => (
            <ListItem
              key={ticket.ticket_id}
              title={ticket.subject}
              subtitle={ticket.status}
              meta={ticket.created_at?.slice(0, 10)}
            />
          ))}
        </ListSection>
        <Button label="Refresh" variant="ghost" onPress={() => void refetch()} />
      </ScrollView>
    </Screen>
  );
}
