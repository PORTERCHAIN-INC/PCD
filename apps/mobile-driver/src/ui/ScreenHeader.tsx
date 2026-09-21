import { Text, View, StyleSheet } from "react-native";
import { colors, typography } from "@porterchain/mobile-theme";
import { DEV_MENU_GUTTER } from "./Screen";

export function ScreenHeader({ title, lede }: { title: string; lede?: string }) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.title}>{title}</Text>
      {lede ? <Text style={styles.lede}>{lede}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    paddingRight: DEV_MENU_GUTTER,
    gap: 4,
  },
  title: { ...typography.title, fontSize: 28, color: colors.primary },
  lede: { ...typography.caption, color: colors.muted },
});
