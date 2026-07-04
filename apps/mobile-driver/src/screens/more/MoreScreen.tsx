import { ScrollView } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useOfflineSync } from "@porterchain/mobile-offline";
import { ListItem, ListSection, Screen } from "@porterchain/mobile-ui";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { MoreStackParamList } from "../../navigation/types";

const links = [
  { label: "Profile", screen: "Profile" as const },
  { label: "Notifications", screen: "Notifications" as const },
  { label: "Offline sync", screen: "OfflineSync" as const },
  { label: "Support", screen: "Support" as const },
  { label: "SOS / Emergency", screen: "Sos" as const },
  { label: "Settings", screen: "Settings" as const },
  { label: "Performance", screen: "Performance" as const },
];

export function MoreScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<MoreStackParamList>>();
  const { localPending, localFailed } = useOfflineSync();

  return (
    <Screen>
      <ScreenHeader title="More" subtitle="Profile & support" />
      <ScrollView>
        <ListSection title="Account">
          {links.map((link) => (
            <ListItem
              key={link.screen}
              title={link.label}
              meta={link.screen === "OfflineSync" && localPending + localFailed > 0 ? `${localPending + localFailed}` : undefined}
              onPress={() => navigation.navigate(link.screen)}
            />
          ))}
        </ListSection>
      </ScrollView>
    </Screen>
  );
}
