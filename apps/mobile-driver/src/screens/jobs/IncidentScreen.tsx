import { useState } from "react";
import { ScrollView } from "react-native";
import { useRoute } from "@react-navigation/native";
import type { RouteProp } from "@react-navigation/native";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Input, Screen } from "@porterchain/mobile-ui";
import { useDriverApi } from "../../api/DriverApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import { getCurrentCoords } from "../../services/location";
import type { JobsStackParamList } from "../../navigation/types";

export function IncidentScreen() {
  const { theme } = useTheme();
  const api = useDriverApi();
  const route = useRoute<RouteProp<JobsStackParamList, "Incident">>();
  const [type, setType] = useState("delivery_issue");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submit() {
    setLoading(true);
    const location = await getCurrentCoords();
    try {
      await api.reportIncident({
        incident_type: type,
        description,
        order_id: route.params?.orderId,
        location: location ?? undefined,
      });
      setMessage("Incident reported.");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader title="Incident" subtitle="Report delivery issue" />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.md }}>
        <Input label="Type" value={type} onChangeText={setType} placeholder="damage | delay | access" />
        <Input label="Description" value={description} onChangeText={setDescription} multiline />
        {message ? <Body muted>{message}</Body> : null}
        <Button label="Submit incident" loading={loading} fullWidth onPress={() => void submit()} />
      </ScrollView>
    </Screen>
  );
}
