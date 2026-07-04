import { useState } from "react";
import { ScrollView } from "react-native";
import { DRIVER_OFFLINE_ACTIONS } from "@porterchain/mobile-api";
import { useOfflineSync } from "@porterchain/mobile-offline";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Input, Screen } from "@porterchain/mobile-ui";
import { useDriverApi } from "../../api/DriverApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";

export function SupportScreen() {
  const { theme } = useTheme();
  const api = useDriverApi();
  const { runDirectOrQueue } = useOfflineSync();
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit() {
    setLoading(true);
    const payload = { subject, description };
    try {
      const result = await runDirectOrQueue(
        DRIVER_OFFLINE_ACTIONS.SUPPORT_TICKET,
        payload,
        () => api.createSupport(payload)
      );
      setMessage(result.mode === "queued" ? "Saved offline." : "Ticket created.");
      setSubject("");
      setDescription("");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader title="Support" subtitle="Driver help desk" />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.md }}>
        <Input label="Subject" value={subject} onChangeText={setSubject} />
        <Input label="Description" value={description} onChangeText={setDescription} multiline />
        {message ? <Body muted>{message}</Body> : null}
        <Button label="Submit" loading={loading} fullWidth onPress={() => void submit()} />
      </ScrollView>
    </Screen>
  );
}
