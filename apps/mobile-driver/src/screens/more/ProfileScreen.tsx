import { useQuery } from "@tanstack/react-query";
import { ScrollView } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Card, CardHeader, Screen } from "@porterchain/mobile-ui";
import { useDriverApi } from "../../api/DriverApiContext";
import { useAuthStore } from "../../store/auth-store";
import { ScreenHeader } from "../../components/ScreenHeader";

export function ProfileScreen() {
  const { theme } = useTheme();
  const api = useDriverApi();
  const clearSession = useAuthStore((s) => s.clearSession);

  const { data } = useQuery({
    queryKey: ["driver", "me"],
    queryFn: () => api.me(),
  });

  return (
    <Screen>
      <ScreenHeader title="Profile" subtitle={data?.full_name} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.lg }}>
        <Card>
          <CardHeader title={data?.full_name ?? "Driver"} subtitle={data?.email} />
          <Body muted>
            Status: {data?.status} · Rating {data?.rating ?? "—"}
          </Body>
          <Body muted>Phone: {data?.phone ?? "—"}</Body>
        </Card>
        <Button label="Sign out" variant="danger" fullWidth onPress={() => void clearSession()} />
      </ScrollView>
    </Screen>
  );
}
