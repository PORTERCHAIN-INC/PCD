import { useState } from "react";
import { ScrollView } from "react-native";
import { CUSTOMER_OFFLINE_ACTIONS } from "@porterchain/mobile-api";
import { useOfflineSync } from "@porterchain/mobile-offline";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Input, Screen } from "@porterchain/mobile-ui";
import { useCustomerApi } from "../../api/CustomerApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";

export function ClaimsScreen() {
  const { theme } = useTheme();
  const api = useCustomerApi();
  const { runDirectOrQueue } = useOfflineSync();

  const [orderId, setOrderId] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submit() {
    setSaving(true);
    setMessage(null);
    const payload = {
      subject: `Claim: order ${orderId}`,
      description,
      order_id: orderId,
    };
    try {
      const result = await runDirectOrQueue(
        CUSTOMER_OFFLINE_ACTIONS.CLAIM_CREATE,
        payload,
        () => api.createSupport(payload)
      );
      setMessage(result.mode === "queued" ? "Claim saved offline — will submit when connected." : "Claim submitted. Our team will review it.");
      setOrderId("");
      setDescription("");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader title="Claims" subtitle="Damage, loss, or delivery issues" />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.md }}>
        <Body muted>Claims are handled via Porterchain support using your order details.</Body>
        <Input label="Order ID" value={orderId} onChangeText={setOrderId} />
        <Input label="What happened?" value={description} onChangeText={setDescription} multiline />
        {message ? <Body muted>{message}</Body> : null}
        <Button label="Submit claim" loading={saving} fullWidth onPress={() => void submit()} />
      </ScrollView>
    </Screen>
  );
}
