/**
 * Full-screen step page for one focused task (signature, ID check, code, problem report, SOS,
 * policy). Slides in over the whole screen with a clear header (← Back + title); nothing is
 * half-covered. The page's action is pinned at the bottom in thumb reach; keyboard-safe.
 * (Kept the `Sheet` name so every caller moved to the new pattern at once.)
 */
import type { ReactNode } from "react";
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaProvider, useSafeAreaInsets } from "react-native-safe-area-context";
import { haptic } from "../haptics";
import { useLayout } from "./layout";
import { PressScale } from "./motion";
import { color, maxFontScale, space, target, type } from "./theme";

export function Sheet(props: {
  visible: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  testID?: string;
  /** Header kicker, e.g. "Stop 3 · Deliver". */
  kicker?: string;
  tone?: "default" | "danger";
}) {
  return (
    <Modal
      visible={props.visible}
      animationType="slide"
      presentationStyle="fullScreen"
      statusBarTranslucent
      navigationBarTranslucent
      onRequestClose={props.onClose}
    >
      <SafeAreaProvider>
        <StepPage {...props} />
      </SafeAreaProvider>
    </Modal>
  );
}

export function StepPage({
  title,
  onClose,
  children,
  footer,
  testID,
  kicker,
  tone = "default",
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  testID?: string;
  kicker?: string;
  tone?: "default" | "danger";
}) {
  const insets = useSafeAreaInsets();
  const L = useLayout();
  const pad = { paddingLeft: insets.left + L.gutter, paddingRight: insets.right + L.gutter };
  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={[styles.page, tone === "danger" && styles.pageDanger]}
      testID={testID}
      accessibilityViewIsModal
    >
      <View style={[styles.header, pad, { paddingTop: insets.top + space.sm }]}>
        <PressScale
          accessibilityRole="button"
          accessibilityLabel="Back"
          onPress={() => {
            haptic.tap();
            onClose();
          }}
          hitSlop={8}
          style={styles.back}
          testID="page-back"
        >
          <Text style={styles.backText}>‹ Back</Text>
        </PressScale>
      </View>
      <ScrollView
        contentContainerStyle={[
          styles.body,
          pad,
          { maxWidth: L.maxContent + insets.left + insets.right },
        ]}
        keyboardShouldPersistTaps="handled"
      >
        {kicker ? (
          <Text style={[styles.kicker, tone === "danger" && styles.kickerDanger]}>{kicker}</Text>
        ) : null}
        <Text style={styles.title} accessibilityRole="header" maxFontSizeMultiplier={maxFontScale}>
          {title}
        </Text>
        {children}
      </ScrollView>
      {footer ? (
        <View style={[styles.footer, pad, { paddingBottom: Math.max(insets.bottom, space.lg) }]}>
          {footer}
        </View>
      ) : null}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: color.bg },
  pageDanger: { backgroundColor: "#12070A" },
  header: { flexDirection: "row", alignItems: "center", paddingBottom: space.xs },
  back: { minHeight: target.min - 8, minWidth: target.min, justifyContent: "center" },
  backText: { ...type.bodyStrong, color: color.inkMuted },
  body: { gap: space.md, paddingBottom: space.xl, width: "100%", alignSelf: "center" },
  kicker: { ...type.label, color: color.primary },
  kickerDanger: { color: color.danger },
  title: { ...type.display, color: color.ink, marginBottom: space.xs },
  footer: {
    gap: space.sm,
    paddingTop: space.md,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: color.border,
    backgroundColor: color.bg,
  },
});
