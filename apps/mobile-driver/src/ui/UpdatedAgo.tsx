/** Subtle "Updated 12s ago" line; a live dot while a background refresh runs. No spinner. */
import { StyleSheet, Text } from "react-native";
import { agoLabel } from "../data/keys";
import { useT } from "../i18n";
import { color } from "./theme";
import { useNow } from "./useNow";

export function UpdatedAgo({
  at,
  fetching,
  offline,
}: {
  at: number;
  fetching?: boolean;
  offline?: boolean;
}) {
  const now = useNow(at > 0, 5000);
  const t = useT();
  if (!at) return null;
  const ago = agoLabel(at, now);
  return (
    <Text style={st.t} accessibilityLiveRegion="none" testID="updated-ago">
      {fetching ? "● " : ""}
      {offline ? "Offline · " : ""}
      {t("updated")} {ago}
    </Text>
  );
}

const st = StyleSheet.create({
  t: { fontSize: 12, lineHeight: 16, color: color.inkFaint, fontWeight: "600" },
});
