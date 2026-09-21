import { Platform, SafeAreaView, StatusBar, View, StyleSheet, type ViewProps } from "react-native";
import { colors, spacing } from "@porterchain/mobile-theme";

type Props = ViewProps & {
  /** False inside FieldShell so the tab bar owns the home-indicator inset. */
  includeBottomSafeArea?: boolean;
};

export const DEV_MENU_GUTTER = 56;

export function Screen({ children, style, includeBottomSafeArea = true, ...rest }: Props) {
  const androidTop = Platform.OS === "android" ? (StatusBar.currentHeight ?? 28) : 0;
  const androidBottom = Platform.OS === "android" && includeBottomSafeArea ? 16 : 0;
  return (
    <SafeAreaView style={[styles.safe, !includeBottomSafeArea && styles.safeFlushBottom]}>
      <View
        style={[
          styles.inner,
          {
            paddingTop: spacing.lg + androidTop,
            paddingBottom: spacing.md + androidBottom,
          },
          style,
        ]}
        {...rest}
      >
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
  safeFlushBottom: {
    paddingBottom: 0,
  },
  inner: {
    flex: 1,
    paddingHorizontal: spacing.xl,
    gap: spacing.md,
  },
});
