import {
  Pressable,
  Text,
  TextInput,
  View,
  StyleSheet,
  type KeyboardTypeOptions,
} from "react-native";
import { colors, radius, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";

type Props = {
  label: string;
  value: string;
  onChange: (next: string) => void;
  placeholder: string;
  suggestions: { label: string; value: string }[];
  keyboardType?: KeyboardTypeOptions;
  accessoryId?: string;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
};

export function SuggestField({
  label,
  value,
  onChange,
  placeholder,
  suggestions,
  keyboardType = "default",
  accessoryId,
  autoCapitalize = "sentences",
}: Props) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        style={styles.input}
        placeholder={placeholder}
        placeholderTextColor={colors.muted}
        value={value}
        onChangeText={onChange}
        keyboardType={keyboardType}
        autoCapitalize={autoCapitalize}
        inputAccessoryViewID={accessoryId}
      />
      <View style={styles.chips}>
        {suggestions.map((item) => {
          const on = value === item.value;
          return (
            <Pressable
              key={item.value}
              accessibilityRole="button"
              accessibilityState={{ selected: on }}
              onPress={() => onChange(on ? "" : item.value)}
              style={on ? styles.chipOn : styles.chip}
            >
              <Text style={on ? styles.chipOnText : styles.chipText}>{item.label}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 8 },
  label: { ...typography.caption, color: colors.muted },
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
  chipOnText: { ...typography.caption, color: colors.white, fontWeight: "700" },
});
