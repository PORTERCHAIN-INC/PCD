import { Pressable, Text, StyleSheet, type PressableProps } from "react-native";
import { colors, radius, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";

type Props = PressableProps & {
  label: string;
  testID?: string;
  tone?: "solid" | "ghost";
};

export function PrimaryButton({ label, testID, disabled, tone = "solid", ...rest }: Props) {
  const ghost = tone === "ghost";
  return (
    <Pressable
      accessibilityRole="button"
      testID={testID}
      disabled={disabled}
      style={[styles.button, ghost && styles.ghost, disabled && styles.disabled]}
      {...rest}
    >
      <Text style={[styles.label, ghost && styles.ghostLabel]}>{label}</Text>
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
  ghost: {
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: `${colors.primary}22`,
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
    color: colors.primary,
  },
});
