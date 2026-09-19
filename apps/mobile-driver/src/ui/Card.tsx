import { View, Text, StyleSheet, type ViewProps } from "react-native";
import { colors, radius, spacing, typography } from "@porterchain/mobile-theme";

export function Card({ children, style, ...rest }: ViewProps) {
  return (
    <View style={[styles.card, style]} {...rest}>
      {children}
    </View>
  );
}

export function CardTitle({ children }: { children: string }) {
  return <Text style={styles.title}>{children}</Text>;
}

export function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.kpi}>
      <Text style={styles.kpiLabel}>{label}</Text>
      <Text style={styles.kpiValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    padding: spacing.md,
    gap: spacing.sm,
  },
  title: {
    ...typography.caption,
    color: colors.muted,
    textTransform: "uppercase",
    letterSpacing: 1,
    fontWeight: "700",
  },
  kpi: {
    flex: 1,
    gap: 2,
  },
  kpiLabel: {
    ...typography.caption,
    color: colors.muted,
  },
  kpiValue: {
    ...typography.title,
    color: colors.primary,
  },
});
