import type { ReactNode } from "react";
import {
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
  type ViewProps,
} from "react-native";
import { spacing, usePalette } from "../theme";
import { Txt } from "./kit";

type Props = ViewProps & {
  /** Large title (iOS style) shown at the top of the scroll content. */
  title?: string;
  subtitle?: string;
  /** Right side of the title row (e.g. a button). */
  headerRight?: ReactNode;
  scroll?: boolean;
  refreshing?: boolean;
  onRefresh?: () => void;
  /** Sticky content pinned under the scroll view (e.g. primary action). */
  footer?: ReactNode;
};

export function Screen({
  children,
  style,
  title,
  subtitle,
  headerRight,
  scroll,
  refreshing,
  onRefresh,
  footer,
  ...rest
}: Props) {
  const c = usePalette();
  const header = title ? (
    <View style={styles.header}>
      <View style={{ flex: 1, gap: 2 }}>
        <Txt v="largeTitle" accessibilityRole="header">
          {title}
        </Txt>
        {subtitle ? (
          <Txt v="callout" tone="muted">
            {subtitle}
          </Txt>
        ) : null}
      </View>
      {headerRight}
    </View>
  ) : null;
  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: c.grayBg }]}>
      {scroll ? (
        <ScrollView
          contentContainerStyle={[styles.inner, style]}
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="interactive"
          refreshControl={
            onRefresh ? (
              <RefreshControl
                refreshing={Boolean(refreshing)}
                onRefresh={onRefresh}
                tintColor={c.muted}
                colors={[c.secondary]}
              />
            ) : undefined
          }
          {...rest}
        >
          {header}
          {children}
        </ScrollView>
      ) : (
        <View style={[styles.inner, styles.fill, style]} {...rest}>
          {header}
          {children}
        </View>
      )}
      {footer ? (
        <View style={[styles.footer, { backgroundColor: c.white, borderTopColor: c.border }]}>
          {footer}
        </View>
      ) : null}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  fill: { flex: 1 },
  inner: {
    paddingHorizontal: spacing.lg + 4,
    paddingTop: spacing.lg,
    paddingBottom: spacing["2xl"],
    gap: spacing.md,
  },
  header: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: spacing.md,
    marginBottom: spacing.xs,
  },
  footer: {
    paddingHorizontal: spacing.lg + 4,
    paddingTop: spacing.md,
    paddingBottom: spacing.md,
    borderTopWidth: StyleSheet.hairlineWidth,
    gap: spacing.sm,
  },
});
