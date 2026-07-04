import { ScrollView, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "@porterchain/mobile-theme";
import {
  Body,
  Button,
  Card,
  CardHeader,
  ListItem,
  ListSection,
  Screen,
} from "@porterchain/mobile-ui";
import { useAuthStore } from "../../store/auth-store";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { ProfileStackParamList } from "../../navigation/types";

const links = [
  { label: "Invoices", screen: "Invoices" as const },
  { label: "Receipts", screen: "Receipts" as const },
  { label: "Support", screen: "Support" as const },
  { label: "Claims", screen: "Claims" as const },
  { label: "Offline sync", screen: "OfflineSync" as const },
  { label: "Settings", screen: "Settings" as const },
  { label: "Performance", screen: "Performance" as const },
];

export function ProfileScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<NativeStackNavigationProp<ProfileStackParamList>>();
  const email = useAuthStore((s) => s.email);
  const clearSession = useAuthStore((s) => s.clearSession);

  return (
    <Screen>
      <ScreenHeader title="Profile" subtitle={email ?? "Signed in"} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.lg }}>
        <Card>
          <CardHeader title="Account" subtitle="Customer portal" />
          <Body muted>Manage billing, support, and app preferences.</Body>
        </Card>

        <ListSection title="Billing & help">
          {links.map((link) => (
            <ListItem
              key={link.screen}
              title={link.label}
              onPress={() => navigation.navigate(link.screen)}
            />
          ))}
        </ListSection>

        <View>
          <Button label="Sign out" variant="danger" fullWidth onPress={() => void clearSession()} />
        </View>
      </ScrollView>
    </Screen>
  );
}
