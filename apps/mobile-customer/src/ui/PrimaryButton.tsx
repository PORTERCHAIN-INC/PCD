import { Pressable, Text, StyleSheet, type PressableProps } from "react-native";
import { colors, radius, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";

type Props = PressableProps & {
  label: string;
  testID?: string;
};

export function PrimaryButton({ label, testID, disabled, ...rest }: Props) {
  return (
    <Pressable
      accessibilityRole="button"
      testID={testID}
      disabled={disabled}
      style={[styles.button, disabled && styles.disabled]}
      {...rest}
    >
      <Text style={styles.label}>{label}</Text>
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
  disabled: {
    opacity: 0.45,
  },
  label: {
    ...typography.button,
    color: colors.white,
    textAlign: "center",
  },
});
