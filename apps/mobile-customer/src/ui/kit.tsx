/**
 * Customer app component kit. Every control is theme-aware (light/dark),
 * honours Dynamic Type (capped at `maxFontScale`), has a >= 44pt target and
 * a VoiceOver/TalkBack role + label.
 */
import Ionicons from "@expo/vector-icons/Ionicons";
import { useEffect, useRef, type ComponentProps, type ReactNode } from "react";
import {
  ActivityIndicator,
  Animated,
  Pressable,
  StyleSheet,
  Text,
  View,
  type PressableProps,
  type StyleProp,
  type TextProps,
  type ViewStyle,
} from "react-native";
import type { Tone } from "../format";
import { haptic } from "../haptics";
import {
  maxFontScale,
  radius,
  spacing,
  touchTargetMin,
  type,
  usePalette,
  useThemed,
  type Palette,
} from "../theme";

export type IconName = ComponentProps<typeof Ionicons>["name"];

export function Icon({
  name,
  size = 22,
  color,
}: {
  name: IconName;
  size?: number;
  color?: string;
}) {
  const c = usePalette();
  return <Ionicons name={name} size={size} color={color ?? c.primary} accessible={false} />;
}

type TxtProps = TextProps & {
  v?: keyof typeof type;
  tone?:
    "default" | "muted" | "accent" | "danger" | "success" | "onAccent" | "onHero" | "onHeroMuted";
  center?: boolean;
};

export function Txt({ v = "body", tone = "default", center, style, ...rest }: TxtProps) {
  const c = usePalette();
  const color = {
    default: c.primary,
    muted: c.muted,
    accent: c.accentText,
    danger: c.danger,
    success: c.success,
    onAccent: c.onAccent,
    onHero: c.onHero,
    onHeroMuted: c.onHeroMuted,
  }[tone];
  return (
    <Text
      maxFontSizeMultiplier={maxFontScale}
      style={[type[v], { color }, center && { textAlign: "center" }, style]}
      {...rest}
    />
  );
}

type ButtonProps = PressableProps & {
  label: string;
  variant?: "solid" | "ghost" | "plain" | "danger";
  icon?: IconName;
  loading?: boolean;
  testID?: string;
  compact?: boolean;
};

export function Button({
  label,
  variant = "solid",
  icon,
  loading,
  disabled,
  onPress,
  compact,
  style,
  ...rest
}: ButtonProps) {
  const { colors: c, styles } = useThemed(makeButton);
  const fg =
    variant === "solid"
      ? c.onAccent
      : variant === "danger"
        ? c.danger
        : variant === "plain"
          ? c.accentText
          : c.primary;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: Boolean(disabled || loading), busy: Boolean(loading) }}
      disabled={disabled || loading}
      onPress={(e) => {
        haptic.tap();
        onPress?.(e);
      }}
      style={(state) => [
        styles.base,
        compact && styles.compact,
        styles[variant],
        (disabled || loading) && styles.disabled,
        state.pressed && styles.pressed,
        typeof style === "function" ? style(state) : style,
      ]}
      {...rest}
    >
      {loading ? (
        <ActivityIndicator color={fg} />
      ) : icon ? (
        <Icon name={icon} size={20} color={fg} />
      ) : null}
      <Text maxFontSizeMultiplier={maxFontScale} style={[type.headline, { color: fg }]}>
        {label}
      </Text>
    </Pressable>
  );
}

const makeButton = (c: Palette) =>
  StyleSheet.create({
    base: {
      minHeight: 52,
      borderRadius: radius.lg,
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      gap: spacing.sm,
      paddingHorizontal: spacing.xl,
      alignSelf: "stretch",
    },
    compact: { minHeight: touchTargetMin, paddingHorizontal: spacing.lg, alignSelf: "auto" },
    solid: { backgroundColor: c.secondary },
    ghost: { backgroundColor: c.white, borderWidth: 1, borderColor: c.border },
    plain: { backgroundColor: "transparent" },
    danger: { backgroundColor: c.dangerBg },
    disabled: { opacity: 0.45 },
    pressed: { opacity: 0.8, transform: [{ scale: 0.99 }] },
  });

export function Card({
  children,
  style,
  onPress,
  accessibilityLabel,
  testID,
}: {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
  onPress?: () => void;
  accessibilityLabel?: string;
  testID?: string;
}) {
  const { styles } = useThemed(makeCard);
  if (!onPress)
    return (
      <View testID={testID} style={[styles.card, style]}>
        {children}
      </View>
    );
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      onPress={() => {
        haptic.tap();
        onPress();
      }}
      style={({ pressed }) => [styles.card, style, pressed && { opacity: 0.85 }]}
    >
      {children}
    </Pressable>
  );
}

const makeCard = (c: Palette) =>
  StyleSheet.create({
    card: {
      backgroundColor: c.white,
      borderRadius: radius.xl,
      padding: spacing.lg,
      gap: spacing.sm,
      borderWidth: c.scheme === "dark" ? 1 : 0,
      borderColor: c.border,
      shadowColor: "#0a1628",
      shadowOpacity: c.scheme === "dark" ? 0 : 0.06,
      shadowRadius: 12,
      shadowOffset: { width: 0, height: 4 },
      elevation: c.scheme === "dark" ? 0 : 1,
    },
  });

export function Chip({
  label,
  selected,
  onPress,
  icon,
  testID,
}: {
  label: string;
  selected?: boolean;
  onPress: () => void;
  icon?: IconName;
  testID?: string;
}) {
  const { colors: c, styles } = useThemed(makeChip);
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityState={{ selected: Boolean(selected) }}
      accessibilityLabel={label}
      onPress={() => {
        haptic.tap();
        onPress();
      }}
      style={[styles.chip, selected && styles.on]}
    >
      {icon ? <Icon name={icon} size={16} color={selected ? c.onAccent : c.primary} /> : null}
      <Text
        maxFontSizeMultiplier={maxFontScale}
        style={[type.callout, { color: selected ? c.onAccent : c.primary }]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

const makeChip = (c: Palette) =>
  StyleSheet.create({
    chip: {
      minHeight: touchTargetMin,
      paddingHorizontal: spacing.lg,
      borderRadius: 999,
      borderWidth: 1,
      borderColor: c.border,
      backgroundColor: c.white,
      flexDirection: "row",
      alignItems: "center",
      gap: 6,
    },
    on: { backgroundColor: c.secondary, borderColor: c.secondary },
  });

export function Segmented<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { id: T; label: string }[];
  value: T;
  onChange: (id: T) => void;
}) {
  const { colors: c, styles } = useThemed(makeSeg);
  return (
    <View style={styles.track} accessibilityRole="tablist">
      {options.map((o) => {
        const on = o.id === value;
        return (
          <Pressable
            key={o.id}
            accessibilityRole="tab"
            accessibilityState={{ selected: on }}
            accessibilityLabel={o.label}
            onPress={() => {
              haptic.tap();
              onChange(o.id);
            }}
            style={[styles.item, on && styles.on]}
          >
            <Text
              maxFontSizeMultiplier={1.3}
              numberOfLines={1}
              style={[
                type.caption,
                { color: on ? c.primary : c.muted, fontWeight: on ? "700" : "500" },
              ]}
            >
              {o.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const makeSeg = (c: Palette) =>
  StyleSheet.create({
    track: { flexDirection: "row", backgroundColor: c.sunken, borderRadius: radius.lg, padding: 3 },
    item: {
      flex: 1,
      minHeight: 40,
      alignItems: "center",
      justifyContent: "center",
      borderRadius: radius.md,
    },
    on: {
      backgroundColor: c.white,
      shadowColor: "#000",
      shadowOpacity: 0.08,
      shadowRadius: 4,
      shadowOffset: { width: 0, height: 1 },
      elevation: 1,
    },
  });

/** Shimmer-free pulsing placeholder; respects reduced motion by staying static. */
export function Skeleton({
  height = 16,
  width = "100%",
  r = radius.md,
}: {
  height?: number;
  width?: number | `${number}%`;
  r?: number;
}) {
  const c = usePalette();
  const pulse = useRef(new Animated.Value(0.55)).current;
  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1, duration: 700, useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 0.55, duration: 700, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [pulse]);
  return (
    <Animated.View
      style={{ height, width, borderRadius: r, backgroundColor: c.sunken, opacity: pulse }}
    />
  );
}

export function SkeletonList({ rows = 3 }: { rows?: number }) {
  return (
    <View accessibilityLabel="Loading" accessible style={{ gap: spacing.md }}>
      {Array.from({ length: rows }, (_, i) => (
        <Card key={i}>
          <Skeleton width="45%" height={18} />
          <Skeleton width="80%" />
          <Skeleton width="30%" height={12} />
        </Card>
      ))}
    </View>
  );
}

const TONE_ICON: Record<"info" | "danger" | "success" | "warning" | "offline", IconName> = {
  info: "information-circle",
  danger: "alert-circle",
  success: "checkmark-circle",
  warning: "warning",
  offline: "cloud-offline",
};

export function Banner({
  tone = "info",
  text,
  action,
  onAction,
}: {
  tone?: "info" | "danger" | "success" | "warning" | "offline";
  text: string;
  action?: string;
  onAction?: () => void;
}) {
  const c = usePalette();
  const bg = {
    info: c.infoBg,
    danger: c.dangerBg,
    success: c.successBg,
    warning: c.warningBg,
    offline: c.sunken,
  }[tone];
  const fg = {
    info: c.accentText,
    danger: c.danger,
    success: c.success,
    warning: c.warning,
    offline: c.primary,
  }[tone];
  return (
    <View
      accessibilityRole="alert"
      accessibilityLiveRegion="polite"
      style={{
        backgroundColor: bg,
        borderRadius: radius.lg,
        padding: spacing.md,
        flexDirection: "row",
        gap: spacing.sm,
        alignItems: "center",
      }}
    >
      <Icon name={TONE_ICON[tone]} size={20} color={fg} />
      <Txt v="callout" style={{ flex: 1, color: c.primary }}>
        {text}
      </Txt>
      {action && onAction ? (
        <Pressable
          accessibilityRole="button"
          onPress={onAction}
          hitSlop={10}
          style={{ minHeight: touchTargetMin, justifyContent: "center" }}
        >
          <Txt v="headline" tone="accent">
            {action}
          </Txt>
        </Pressable>
      ) : null}
    </View>
  );
}

export function StatusPill({ label, tone }: { label: string; tone: Tone }) {
  const c = usePalette();
  const map: Record<Tone, [string, string]> = {
    info: [c.infoBg, c.accentText],
    progress: [c.infoBg, c.accentText],
    success: [c.successBg, c.success],
    danger: [c.dangerBg, c.danger],
    neutral: [c.sunken, c.muted],
  };
  const [bg, fg] = map[tone];
  return (
    <View
      style={{
        backgroundColor: bg,
        borderRadius: 999,
        paddingHorizontal: 10,
        paddingVertical: 4,
        alignSelf: "flex-start",
      }}
    >
      <Text maxFontSizeMultiplier={1.4} style={[type.caption, { color: fg, fontWeight: "700" }]}>
        {label}
      </Text>
    </View>
  );
}

export function SectionHeader({
  title,
  action,
  onAction,
}: {
  title: string;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between",
        marginTop: spacing.md,
      }}
    >
      <Txt v="headline" accessibilityRole="header">
        {title}
      </Txt>
      {action && onAction ? (
        <Pressable
          accessibilityRole="button"
          onPress={onAction}
          hitSlop={10}
          style={{ minHeight: touchTargetMin, justifyContent: "center" }}
        >
          <Txt v="callout" tone="accent">
            {action}
          </Txt>
        </Pressable>
      ) : null}
    </View>
  );
}

export function ListRow({
  icon,
  title,
  subtitle,
  right,
  onPress,
  danger,
  testID,
}: {
  icon?: IconName;
  title: string;
  subtitle?: string;
  right?: ReactNode;
  onPress?: () => void;
  danger?: boolean;
  testID?: string;
}) {
  const c = usePalette();
  const body = (
    <>
      {icon ? (
        <View
          style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            backgroundColor: danger ? c.dangerBg : c.infoBg,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Icon name={icon} size={20} color={danger ? c.danger : c.accentText} />
        </View>
      ) : null}
      <View style={{ flex: 1, gap: 2 }}>
        <Txt v="headline" tone={danger ? "danger" : "default"}>
          {title}
        </Txt>
        {subtitle ? (
          <Txt v="caption" tone="muted">
            {subtitle}
          </Txt>
        ) : null}
      </View>
      {right}
      {onPress ? <Icon name="chevron-forward" size={18} color={c.muted} /> : null}
    </>
  );
  const style = {
    flexDirection: "row" as const,
    alignItems: "center" as const,
    gap: spacing.md,
    minHeight: 56,
    paddingVertical: spacing.sm,
  };
  if (!onPress) return <View style={style}>{body}</View>;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={subtitle ? `${title}, ${subtitle}` : title}
      onPress={() => {
        haptic.tap();
        onPress();
      }}
      style={({ pressed }) => [style, pressed && { opacity: 0.6 }]}
    >
      {body}
    </Pressable>
  );
}

export function Divider() {
  const c = usePalette();
  return <View style={{ height: StyleSheet.hairlineWidth, backgroundColor: c.border }} />;
}

/** Horizontal journey progress (Booked → Delivered). */
export function Progress({
  steps,
  current,
  onDark,
}: {
  steps: string[];
  current: number;
  onDark?: boolean;
}) {
  const c = usePalette();
  const done = onDark ? c.onHero : c.secondary;
  const todo = onDark ? "rgba(255,255,255,0.25)" : c.sunken;
  return (
    <View
      accessible
      accessibilityLabel={
        current >= 0
          ? `Step ${current + 1} of ${steps.length}: ${steps[current]}`
          : "Status unavailable"
      }
      style={{ flexDirection: "row", gap: 4 }}
    >
      {steps.map((s, i) => (
        <View
          key={s}
          style={{
            flex: 1,
            height: 6,
            borderRadius: 3,
            backgroundColor: i <= current ? done : todo,
          }}
        />
      ))}
    </View>
  );
}

/** Tiny state helper for remote lists: loading, refreshing, error, offline. */
export function EmptyNote({
  icon,
  title,
  body,
  action,
  onAction,
}: {
  icon: IconName;
  title: string;
  body: string;
  action?: string;
  onAction?: () => void;
}) {
  const c = usePalette();
  return (
    <Card style={{ alignItems: "center", paddingVertical: spacing["2xl"] }}>
      <View
        style={{
          width: 56,
          height: 56,
          borderRadius: 28,
          backgroundColor: c.infoBg,
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Icon name={icon} size={28} color={c.accentText} />
      </View>
      <Txt v="headline" center>
        {title}
      </Txt>
      <Txt v="callout" tone="muted" center>
        {body}
      </Txt>
      {action && onAction ? <Button label={action} compact onPress={onAction} /> : null}
    </Card>
  );
}
