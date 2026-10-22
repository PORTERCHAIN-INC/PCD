import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import {
  DELIVERY_FLAGS,
  DELIVERY_TEXT_LIMITS,
  DROP_METHODS,
  type DeliveryOptions,
} from "@porterchain/types";
import { radius, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";
import { useThemed, type Palette } from "../theme";

type Props = {
  value: DeliveryOptions;
  onChange: (next: DeliveryOptions) => void;
  accessoryId?: string;
};

/** Shared delivery options (same set as web, admin, Shopify, driver and label). */
export function DeliveryOptionsField({ value, onChange, accessoryId }: Props) {
  const { colors, styles } = useThemed(makeStyles);
  const set = (patch: Partial<DeliveryOptions>) => onChange({ ...value, ...patch });
  const chip = (on: boolean, label: string, onPress: () => void, key: string) => (
    <Pressable
      key={key}
      accessibilityRole="button"
      accessibilityState={{ selected: on }}
      onPress={onPress}
      style={on ? styles.chipOn : styles.chip}
      testID={`dlv-${key}`}
    >
      <Text style={on ? styles.chipOnText : styles.chipText}>{label}</Text>
    </Pressable>
  );
  return (
    <View style={styles.wrap}>
      <Text style={styles.label}>Delivery options</Text>
      <View style={styles.chips}>
        {DROP_METHODS.map((m) =>
          chip(
            value.drop_method === m.id,
            m.label,
            () => set({ drop_method: value.drop_method === m.id ? null : m.id }),
            m.id
          )
        )}
        {DELIVERY_FLAGS.map((f) =>
          chip(Boolean(value[f.id]), f.label, () => set({ [f.id]: !value[f.id] }), f.id)
        )}
      </View>
      <View style={styles.row}>
        <TextInput
          accessibilityLabel="Apartment or unit"
          style={[styles.input, styles.half]}
          placeholder="Apt / unit"
          placeholderTextColor={colors.muted}
          maxLength={DELIVERY_TEXT_LIMITS.unit}
          value={value.unit ?? ""}
          onChangeText={(unit) => set({ unit })}
          inputAccessoryViewID={accessoryId}
        />
        <TextInput
          accessibilityLabel="Buzzer code"
          style={[styles.input, styles.half]}
          placeholder="Buzzer code"
          placeholderTextColor={colors.muted}
          maxLength={DELIVERY_TEXT_LIMITS.buzzer}
          value={value.buzzer ?? ""}
          onChangeText={(buzzer) => set({ buzzer })}
          inputAccessoryViewID={accessoryId}
        />
      </View>
    </View>
  );
}

const makeStyles = (colors: Palette) =>
  StyleSheet.create({
    wrap: { gap: 8 },
    label: { ...typography.caption, color: colors.muted },
    row: { flexDirection: "row", gap: 8 },
    half: { flex: 1 },
    input: {
      minHeight: touchTargetMin,
      borderWidth: 1,
      borderColor: `${colors.primary}26`,
      borderRadius: radius.lg,
      paddingHorizontal: spacing.md,
      backgroundColor: colors.white,
      color: colors.primary,
      fontSize: typography.body.fontSize,
    },
    chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
    chip: {
      backgroundColor: colors.white,
      borderRadius: 999,
      borderWidth: 1,
      borderColor: `${colors.primary}18`,
      paddingHorizontal: 12,
      paddingVertical: 8,
    },
    chipOn: {
      backgroundColor: colors.secondary,
      borderRadius: 999,
      paddingHorizontal: 12,
      paddingVertical: 8,
    },
    chipText: { ...typography.caption, color: colors.primary, fontWeight: "600" },
    chipOnText: { ...typography.caption, color: colors.onAccent, fontWeight: "700" },
  });
