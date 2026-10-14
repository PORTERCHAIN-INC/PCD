/** Compact settings rows: section card, tap row, switch row, segmented choice. 52 pt rows. */
import type { ReactNode } from "react";
import { StyleSheet, Switch, Text, TextInput, View, type TextInputProps } from "react-native";
import { haptic } from "../../haptics";
import { PressScale } from "../motion";
import { color, radius, space, type } from "../theme";

export function Section({
  title,
  children,
  testID,
}: {
  title: string;
  children: ReactNode;
  testID?: string;
}) {
  return (
    <View style={st.section} testID={testID}>
      <Text style={st.sectionTitle} accessibilityRole="header">
        {title}
      </Text>
      <View style={st.card}>{children}</View>
    </View>
  );
}

export function Row({
  label,
  value,
  onPress,
  tone,
  sub,
  testID,
  badge,
}: {
  label: string;
  value?: string;
  sub?: string;
  onPress?: () => void;
  tone?: "danger" | "accent";
  testID?: string;
  badge?: number;
}) {
  const body = (
    <>
      <View style={st.flex}>
        <Text
          style={[st.label, tone === "danger" && st.danger, tone === "accent" && st.accent]}
          numberOfLines={1}
        >
          {label}
        </Text>
        {sub ? (
          <Text style={st.sub} numberOfLines={2}>
            {sub}
          </Text>
        ) : null}
      </View>
      {badge ? (
        <View style={st.badge}>
          <Text style={st.badgeText}>{badge}</Text>
        </View>
      ) : null}
      {value ? (
        <Text style={st.value} numberOfLines={1}>
          {value}
        </Text>
      ) : null}
      {onPress ? <Text style={st.chev}>›</Text> : null}
    </>
  );
  if (!onPress)
    return (
      <View style={st.row} testID={testID}>
        {body}
      </View>
    );
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel={value ? `${label}, ${value}` : label}
      onPress={() => {
        haptic.tap();
        onPress();
      }}
      style={st.row}
      testID={testID}
    >
      {body}
    </PressScale>
  );
}

export function ToggleRow({
  label,
  sub,
  value,
  onChange,
  testID,
}: {
  label: string;
  sub?: string;
  value: boolean;
  onChange: (v: boolean) => void;
  testID?: string;
}) {
  return (
    <View style={st.row} testID={testID}>
      <View style={st.flex}>
        <Text style={st.label}>{label}</Text>
        {sub ? <Text style={st.sub}>{sub}</Text> : null}
      </View>
      <Switch
        accessibilityLabel={label}
        value={value}
        onValueChange={(v) => {
          haptic.tap();
          onChange(v);
        }}
        trackColor={{ false: color.surface2, true: color.primary }}
        thumbColor={color.ink}
        ios_backgroundColor={color.surface2}
      />
    </View>
  );
}

export function Segmented<T extends string | number>({
  label,
  options,
  value,
  onChange,
  testID,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
  testID?: string;
}) {
  return (
    <View style={st.segWrap} testID={testID}>
      <Text style={st.label}>{label}</Text>
      <View style={st.seg} accessibilityRole="radiogroup">
        {options.map((o) => {
          const on = o.value === value;
          return (
            <PressScale
              key={String(o.value)}
              accessibilityRole="radio"
              accessibilityState={{ selected: on }}
              onPress={() => {
                haptic.tap();
                onChange(o.value);
              }}
              style={[st.segItem, on && st.segOn]}
            >
              <Text style={[st.segText, on && st.segTextOn]} numberOfLines={1}>
                {o.label}
              </Text>
            </PressScale>
          );
        })}
      </View>
    </View>
  );
}

export const Divider = () => <View style={st.divider} />;

const st = StyleSheet.create({
  section: { gap: space.xs + 2 },
  sectionTitle: { ...type.label, color: color.inkFaint, paddingHorizontal: space.xs },
  card: {
    backgroundColor: color.surface,
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: color.border,
    overflow: "hidden",
  },
  row: {
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    paddingHorizontal: space.lg,
    paddingVertical: space.sm + 2,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: color.border,
  },
  flex: { flex: 1 },
  label: { fontSize: 16, lineHeight: 21, fontWeight: "700", color: color.ink },
  danger: { color: color.danger },
  accent: { color: color.primary },
  sub: { fontSize: 13, lineHeight: 18, color: color.inkMuted, marginTop: 2 },
  value: { fontSize: 15, color: color.inkMuted, maxWidth: "45%" },
  chev: { fontSize: 22, color: color.inkFaint, marginTop: -2 },
  badge: {
    minWidth: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: color.danger,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 6,
  },
  badgeText: { fontSize: 13, fontWeight: "900", color: color.onDanger },
  segWrap: {
    gap: space.sm,
    paddingHorizontal: space.lg,
    paddingVertical: space.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: color.border,
  },
  seg: {
    flexDirection: "row",
    backgroundColor: color.bg,
    borderRadius: radius.md,
    padding: 3,
    gap: 3,
  },
  segItem: {
    flex: 1,
    minHeight: 40,
    borderRadius: radius.sm + 1,
    alignItems: "center",
    justifyContent: "center",
  },
  segOn: { backgroundColor: color.surface2 },
  segText: { fontSize: 14, fontWeight: "700", color: color.inkMuted },
  segTextOn: { color: color.ink },
  divider: { height: space.sm },
});

/** Labelled text input row in the same card language (52 pt, high contrast). */
export function InputRow({
  label,
  value,
  onChange,
  testID,
  error,
  ...rest
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  testID?: string;
  error?: string | null;
} & Omit<TextInputProps, "value" | "onChangeText" | "onChange">) {
  return (
    <View style={inSt.row}>
      <Text style={inSt.label}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChange}
        placeholderTextColor={color.inkFaint}
        style={inSt.input}
        accessibilityLabel={label}
        testID={testID}
        {...rest}
      />
      {error ? <Text style={inSt.err}>{error}</Text> : null}
    </View>
  );
}

const inSt = StyleSheet.create({
  row: {
    paddingHorizontal: space.lg,
    paddingVertical: space.sm + 2,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: color.border,
    gap: 4,
  },
  label: { ...type.label, color: color.inkFaint },
  input: {
    fontSize: 17,
    lineHeight: 22,
    fontWeight: "600",
    color: color.ink,
    minHeight: 32,
    padding: 0,
  },
  err: { fontSize: 13, color: color.danger },
});
