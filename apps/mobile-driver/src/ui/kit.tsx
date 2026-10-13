/** The whole component kit: Screen, text, Button, Banner, Card, EmptyState, TabBar. */
import type { ReactNode } from "react";
import {
  ActivityIndicator,
  Platform,
  Pressable,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
  type TextProps,
} from "react-native";
import { touchTargetMin } from "@porterchain/mobile-theme";
import { haptic } from "../haptics";
import { PressScale } from "./motion";
import { color, maxFontScale, radius, space, target, type } from "./theme";

export function Screen({
  children,
  footer,
  testID,
  scroll = true,
  onRefresh,
  refreshing = false,
}: {
  children: ReactNode;
  /** Pull down to refresh. */
  onRefresh?: () => void;
  refreshing?: boolean;
  /** Pinned under the content: the one primary action lives here, always in thumb reach. */
  footer?: ReactNode;
  testID?: string;
  scroll?: boolean;
}) {
  const top = Platform.OS === "android" ? (StatusBar.currentHeight ?? 24) : 0;
  return (
    <SafeAreaView style={[s.safe, { paddingTop: top }]} testID={testID}>
      {scroll ? (
        <ScrollView
          contentContainerStyle={s.content}
          keyboardShouldPersistTaps="handled"
          refreshControl={
            onRefresh ? <RefreshControl refreshing={refreshing} onRefresh={onRefresh} /> : undefined
          }
        >
          {children}
        </ScrollView>
      ) : (
        <View style={[s.content, s.flex]}>{children}</View>
      )}
      {footer ? <View style={s.footer}>{footer}</View> : null}
    </SafeAreaView>
  );
}

export const Title = (p: TextProps) => (
  <Text
    accessibilityRole="header"
    maxFontSizeMultiplier={maxFontScale}
    {...p}
    style={[s.title, p.style]}
  />
);
export const Heading = (p: TextProps) => (
  <Text
    accessibilityRole="header"
    maxFontSizeMultiplier={maxFontScale}
    {...p}
    style={[s.heading, p.style]}
  />
);
export const Body = (p: TextProps) => (
  <Text maxFontSizeMultiplier={maxFontScale} {...p} style={[s.body, p.style]} />
);
export const Strong = (p: TextProps) => (
  <Text maxFontSizeMultiplier={maxFontScale} {...p} style={[s.strong, p.style]} />
);
export const Muted = (p: TextProps) => (
  <Text maxFontSizeMultiplier={maxFontScale} {...p} style={[s.muted, p.style]} />
);
export const Label = (p: TextProps) => (
  <Text maxFontSizeMultiplier={maxFontScale} {...p} style={[s.label, p.style]} />
);

type Tone = "primary" | "secondary" | "danger" | "quiet";

export function Button({
  label,
  onPress,
  tone = "secondary",
  busy = false,
  disabled = false,
  hint,
  testID,
}: {
  label: string;
  onPress: () => void;
  tone?: Tone;
  busy?: boolean;
  disabled?: boolean;
  /** Read by screen readers: what happens when tapped. */
  hint?: string;
  testID?: string;
}) {
  const off = disabled || busy;
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityHint={hint}
      accessibilityState={{ disabled: off, busy }}
      disabled={off}
      onPress={() => {
        if (tone === "primary" || tone === "danger") haptic.press();
        else haptic.tap();
        onPress();
      }}
      testID={testID}
      style={[
        s.btn,
        tone === "primary" && s.btnPrimary,
        tone === "secondary" && s.btnSecondary,
        tone === "danger" && s.btnDanger,
        tone === "quiet" && s.btnQuiet,
        off && tone !== "quiet" && s.btnDisabled,
      ]}
    >
      {busy ? (
        <ActivityIndicator
          color={
            tone === "primary" ? color.onPrimary : tone === "danger" ? color.onDanger : color.ink
          }
        />
      ) : (
        <Text
          maxFontSizeMultiplier={1.3}
          style={[
            s.btnText,
            tone === "primary" && s.btnTextOn,
            tone === "danger" && s.btnTextOnDanger,
            tone === "quiet" && s.btnTextQuiet,
            off && s.btnTextDisabled,
          ]}
        >
          {label}
        </Text>
      )}
    </PressScale>
  );
}

type BannerTone = "info" | "warn" | "danger" | "success";
const bannerColors: Record<BannerTone, { bg: string; ink: string }> = {
  info: { bg: color.infoSoft, ink: color.infoInk },
  warn: { bg: color.warnSoft, ink: color.warnInk },
  danger: { bg: color.dangerSoft, ink: color.danger },
  success: { bg: color.successSoft, ink: color.successInk },
};

export function Banner({
  tone,
  title,
  body,
  action,
  testID,
}: {
  tone: BannerTone;
  title: string;
  body?: string | null;
  action?: { label: string; onPress: () => void };
  testID?: string;
}) {
  const c = bannerColors[tone];
  return (
    <View
      style={[s.banner, { backgroundColor: c.bg, borderLeftColor: c.ink }]}
      accessibilityRole={tone === "danger" ? "alert" : "summary"}
      accessibilityLiveRegion="polite"
      testID={testID}
    >
      <Text style={[s.strong, { color: c.ink }]}>{title}</Text>
      {body ? <Text style={[s.small, { color: c.ink }]}>{body}</Text> : null}
      {action ? (
        <Pressable
          accessibilityRole="button"
          onPress={action.onPress}
          style={s.bannerAction}
          hitSlop={8}
        >
          <Text style={[s.label, { color: c.ink, textDecorationLine: "underline" }]}>
            {action.label}
          </Text>
        </Pressable>
      ) : null}
    </View>
  );
}

export function Card({ children, testID }: { children: ReactNode; testID?: string }) {
  return (
    <View style={s.card} testID={testID}>
      {children}
    </View>
  );
}

export function EmptyState({
  title,
  body,
  testID,
}: {
  title: string;
  body: string;
  testID?: string;
}) {
  return (
    <View style={s.empty} testID={testID}>
      <Text style={s.emptyMark} accessibilityElementsHidden importantForAccessibility="no">
        ◎
      </Text>
      <Heading style={s.center}>{title}</Heading>
      <Body style={[s.center, { color: color.inkMuted }]}>{body}</Body>
    </View>
  );
}

export type TabId = "today" | "job" | "me";
const TABS: Array<{ id: TabId; label: string }> = [
  { id: "today", label: "Today" },
  { id: "job", label: "Job" },
  { id: "me", label: "Me" },
];

export function TabBar({
  tab,
  onTab,
  jobBadge,
}: {
  tab: TabId;
  onTab: (t: TabId) => void;
  /** Dot on the Job tab when there is work waiting. */
  jobBadge?: boolean;
}) {
  return (
    <View style={s.tabs} accessibilityRole="tablist">
      {TABS.map((t) => {
        const on = t.id === tab;
        return (
          <Pressable
            key={t.id}
            accessibilityRole="tab"
            accessibilityState={{ selected: on }}
            accessibilityLabel={t.id === "job" && jobBadge ? `${t.label}, work waiting` : t.label}
            onPress={() => {
              haptic.tap();
              onTab(t.id);
            }}
            style={[s.tab, on && s.tabOn]}
            testID={`tab-${t.id}`}
          >
            <Text style={[s.tabText, on && s.tabTextOn]}>{t.label}</Text>
            {t.id === "job" && jobBadge ? <View style={s.dot} /> : null}
          </Pressable>
        );
      })}
    </View>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.bg },
  flex: { flex: 1 },
  content: { padding: space.lg, gap: space.md, paddingBottom: space.xxl },
  footer: {
    paddingHorizontal: space.lg,
    paddingTop: space.md,
    paddingBottom: space.lg,
    gap: space.sm,
    backgroundColor: color.bg,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: color.border,
  },
  title: { ...type.title, color: color.ink },
  heading: { ...type.heading, color: color.ink },
  body: { ...type.body, color: color.ink },
  strong: { ...type.bodyStrong, color: color.ink },
  muted: { ...type.small, color: color.inkMuted },
  small: { ...type.small },
  label: { ...type.label, color: color.inkFaint, textTransform: "uppercase" },
  btn: {
    minHeight: target.min,
    borderRadius: radius.lg,
    paddingHorizontal: space.lg,
    alignItems: "center",
    justifyContent: "center",
  },
  btnPrimary: {
    backgroundColor: color.primary,
    minHeight: target.primary,
    shadowColor: color.primary,
    shadowOpacity: 0.35,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
  btnSecondary: { backgroundColor: color.surface2, borderWidth: 1, borderColor: color.border },
  btnDanger: { backgroundColor: color.danger },
  btnQuiet: { backgroundColor: "transparent", minHeight: touchTargetMin + 4 },
  btnDisabled: { backgroundColor: color.disabled, borderColor: color.disabled },
  btnText: { ...type.button, color: color.ink, textAlign: "center" },
  btnTextOn: { color: color.onPrimary },
  btnTextOnDanger: { color: color.onDanger },
  btnTextQuiet: { ...type.bodyStrong, textDecorationLine: "underline" },
  btnTextDisabled: { color: color.onDisabled },
  banner: {
    borderRadius: radius.md,
    borderLeftWidth: 4,
    padding: space.md,
    gap: space.xs,
  },
  bannerAction: { paddingTop: space.xs, minHeight: 32, justifyContent: "center" },
  card: {
    backgroundColor: color.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: color.border,
    borderRadius: radius.lg,
    padding: space.lg,
    gap: space.sm,
  },
  empty: { alignItems: "center", padding: space.xxl, gap: space.sm },
  emptyMark: { fontSize: 48, color: color.border },
  center: { textAlign: "center" },
  tabs: {
    flexDirection: "row",
    backgroundColor: color.bg,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: color.border,
    paddingBottom: Platform.OS === "ios" ? space.lg : space.sm,
  },
  tab: {
    flex: 1,
    minHeight: target.min + 8,
    alignItems: "center",
    justifyContent: "center",
    borderTopWidth: 3,
    borderTopColor: "transparent",
  },
  tabOn: { borderTopColor: color.primary },
  tabText: { ...type.bodyStrong, color: color.inkMuted },
  tabTextOn: { color: color.ink },
  dot: {
    position: "absolute",
    top: 12,
    right: "30%",
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: color.danger,
  },
});
