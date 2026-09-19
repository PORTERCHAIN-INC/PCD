import { SafeAreaView, View, StyleSheet, type ViewProps } from "react-native";
import { colors, spacing } from "@porterchain/mobile-theme";

export function Screen({ children, style, ...rest }: ViewProps) {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={[styles.inner, style]} {...rest}>
        {children}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.grayBg,
  },
  inner: {
    flex: 1,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.lg,
    paddingBottom: spacing.md,
    gap: spacing.md,
  },
});
