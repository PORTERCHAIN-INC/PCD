import { Pressable, Text, StyleSheet, type PressableProps } from "react-native";
import { colors, radius, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";

type Props = PressableProps & {
  label: string;
  testID?: string;
  tone?: "primary" | "danger" | "ghost";
};

export function PrimaryButton({ label, testID, tone = "primary", disabled, ...rest }: Props) {
  return (
    <Pressable
      accessibilityRole="button"
      testID={testID}
      disabled={disabled}
      style={[
        styles.button,
        tone === "danger" && styles.danger,
        tone === "ghost" && styles.ghost,
        disabled && styles.disabled,
      ]}
      {...rest}
    >
      <Text style={[styles.label, tone === "ghost" && styles.ghostLabel]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    backgroundColor: colors.secondary,
    borderRadius: radius.lg,
    minHeight: Math.max(touchTargetMin, 56),
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    width: "100%",
  },
  danger: {
    backgroundColor: colors.danger,
  },
  ghost: {
    backgroundColor: colors.white,
    borderWidth: 1.5,
    borderColor: colors.secondary,
  },
  disabled: {
    opacity: 0.45,
  },
  label: {
    ...typography.button,
    color: colors.white,
    textAlign: "center",
  },
  ghostLabel: {
    color: colors.secondary,
  },
});
