import { useState } from "react";
import { Modal, Pressable, ScrollView, Text, View, StyleSheet } from "react-native";
import { colors, radius, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";
import type { ConsentDocument } from "./consentCopy";
import { PrimaryButton } from "./PrimaryButton";

type Props = {
  label: string;
  checked: boolean;
  document: ConsentDocument;
  onChange: (accepted: boolean) => void;
};

export function ConsentCheck({ label, checked, document, onChange }: Props) {
  const [open, setOpen] = useState(false);

  function openStatement() {
    setOpen(true);
  }

  function accept() {
    onChange(true);
    setOpen(false);
  }

  return (
    <>
      <View style={styles.row}>
        <Pressable
          accessibilityRole="checkbox"
          accessibilityState={{ checked }}
          accessibilityLabel={label}
          hitSlop={8}
          onPress={() => {
            if (checked) onChange(false);
            else openStatement();
          }}
          style={styles.boxHit}
        >
          <View style={[styles.box, checked && styles.boxOn]}>
            {checked ? <Text style={styles.tick}>✓</Text> : null}
          </View>
        </Pressable>
        <Pressable accessibilityRole="link" onPress={openStatement} style={styles.linkHit}>
          <Text style={styles.link}>{label}</Text>
        </Pressable>
      </View>
      <Modal
        visible={open}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setOpen(false)}
      >
        <View style={styles.sheet}>
          <View style={styles.sheetHeader}>
            <Text style={styles.sheetTitle}>{document.title}</Text>
            <Pressable accessibilityRole="button" hitSlop={8} onPress={() => setOpen(false)}>
              <Text style={styles.close}>Close</Text>
            </Pressable>
          </View>
          <Text style={styles.updated}>{document.updated}</Text>
          <ScrollView contentContainerStyle={styles.sheetBody} showsVerticalScrollIndicator>
            <Text style={styles.intro}>{document.intro}</Text>
            {document.sections.map((section) => (
              <View key={section.title} style={styles.section}>
                <Text style={styles.sectionTitle}>{section.title}</Text>
                {section.paragraphs.map((paragraph) => (
                  <Text key={paragraph} style={styles.paragraph}>
                    {paragraph}
                  </Text>
                ))}
                {section.list?.map((item) => (
                  <Text key={item} style={styles.bullet}>
                    · {item}
                  </Text>
                ))}
              </View>
            ))}
          </ScrollView>
          <View style={styles.footer}>
            <PrimaryButton label={checked ? "Accepted" : "Accept"} onPress={accept} />
          </View>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.md,
    minHeight: touchTargetMin,
  },
  boxHit: {
    minWidth: touchTargetMin,
    minHeight: touchTargetMin,
    alignItems: "center",
    justifyContent: "center",
  },
  box: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 1.5,
    borderColor: colors.primary,
    backgroundColor: colors.white,
    alignItems: "center",
    justifyContent: "center",
  },
  boxOn: {
    backgroundColor: colors.secondary,
    borderColor: colors.secondary,
  },
  tick: {
    color: colors.white,
    fontSize: 14,
    fontWeight: "700",
    lineHeight: 16,
  },
  linkHit: {
    flex: 1,
    justifyContent: "center",
    minHeight: touchTargetMin,
    paddingVertical: spacing.sm,
  },
  link: {
    ...typography.body,
    color: colors.secondary,
    textDecorationLine: "underline",
  },
  sheet: {
    flex: 1,
    backgroundColor: colors.white,
    paddingTop: spacing.lg,
  },
  sheetHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.xl,
    gap: spacing.md,
  },
  sheetTitle: {
    ...typography.title,
    flex: 1,
    color: colors.primary,
  },
  close: {
    ...typography.body,
    color: colors.secondary,
    fontWeight: "700",
  },
  updated: {
    ...typography.caption,
    color: colors.muted,
    paddingHorizontal: spacing.xl,
    marginTop: spacing.xs,
  },
  sheetBody: {
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xl,
    gap: spacing.md,
  },
  intro: {
    ...typography.body,
    color: colors.primary,
  },
  section: {
    gap: spacing.sm,
  },
  sectionTitle: {
    ...typography.body,
    color: colors.primary,
    fontWeight: "700",
  },
  paragraph: {
    ...typography.body,
    color: colors.primary,
  },
  bullet: {
    ...typography.caption,
    color: colors.primary,
  },
  footer: {
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.md,
    paddingBottom: spacing.xl,
    borderTopWidth: 1,
    borderTopColor: `${colors.primary}14`,
    backgroundColor: colors.white,
  },
});
