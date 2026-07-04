import { useState } from "react";
import { View } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Screen } from "@porterchain/mobile-ui";
import { useDriverApi } from "../../api/DriverApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import { getCurrentCoords } from "../../services/location";

export function SosScreen() {
  const { theme } = useTheme();
  const api = useDriverApi();
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function triggerSos() {
    setLoading(true);
    setError(null);
    try {
      const location = await getCurrentCoords();
      await api.emergency({
        message: "SOS — driver needs immediate assistance",
        location: location ?? undefined,
      });
      setSent(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "SOS failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader title="SOS" subtitle="Emergency assistance" />
      <View
        style={{
          flex: 1,
          padding: theme.spacing["2xl"],
          justifyContent: "center",
          gap: theme.spacing.lg,
        }}
      >
        <Body muted>
          Triggers Porterchain emergency endpoint. Operations and support are notified server-side —
          no direct Fleetbase call from mobile.
        </Body>
        {sent ? (
          <Body style={{ color: theme.colors.success, textAlign: "center", fontWeight: "600" }}>
            Emergency signal sent.
          </Body>
        ) : null}
        {error ? <Body style={{ color: theme.colors.danger }}>{error}</Body> : null}
        <Button
          label="Send SOS"
          variant="danger"
          loading={loading}
          fullWidth
          onPress={() => void triggerSos()}
        />
      </View>
    </Screen>
  );
}
