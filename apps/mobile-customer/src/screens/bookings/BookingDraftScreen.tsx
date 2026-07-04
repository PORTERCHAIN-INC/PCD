import { useEffect, useState } from "react";
import { ScrollView } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Input, Screen } from "@porterchain/mobile-ui";
import { useCustomerApi } from "../../api/CustomerApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import { useSettingsStore } from "../../store/settings-store";
import type { BookingsStackParamList } from "../../navigation/types";

export function BookingDraftScreen() {
  const { theme } = useTheme();
  const api = useCustomerApi();
  const navigation = useNavigation<NativeStackNavigationProp<BookingsStackParamList>>();
  const ensureVisitorSession = useSettingsStore((s) => s.ensureVisitorSession);

  const [pickup, setPickup] = useState("");
  const [dropoff, setDropoff] = useState("");
  const [draftId, setDraftId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const sessionId = ensureVisitorSession();
    void (async () => {
      try {
        const active = await api.getActiveDraft(sessionId);
        setDraftId(active.draft_id);
        setPickup(active.pickup?.formatted ?? "");
        setDropoff(active.dropoff?.formatted ?? "");
      } catch {
        setDraftId(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [api, ensureVisitorSession]);

  async function saveDraft() {
    const sessionId = ensureVisitorSession();
    setSaving(true);
    try {
      if (draftId) {
        await api.updateDraft(draftId, sessionId, {
          pickup: { formatted: pickup },
          dropoff: { formatted: dropoff },
          current_step: "addresses",
        });
      } else {
        const created = await api.createDraft({
          session_id: sessionId,
          pickup: { formatted: pickup },
          dropoff: { formatted: dropoff },
          current_step: "addresses",
        });
        setDraftId(created.draft_id);
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader title="Booking draft" subtitle="Resume where you left off" />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.md }}>
        {loading ? <Body muted>Loading draft…</Body> : null}
        <Input label="Pickup" value={pickup} onChangeText={setPickup} />
        <Input label="Dropoff" value={dropoff} onChangeText={setDropoff} />
        <Button label="Save draft" variant="secondary" loading={saving} fullWidth onPress={() => void saveDraft()} />
        <Button
          label="Continue to quote"
          fullWidth
          onPress={() => navigation.navigate("Quote")}
          disabled={!pickup || !dropoff}
        />
      </ScrollView>
    </Screen>
  );
}
