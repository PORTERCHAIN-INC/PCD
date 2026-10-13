/**
 * Settings: one compact, scrollable full-screen page. Every change saves on the phone at once
 * and syncs to the server in the background (PUT /settings); nothing waits on the network.
 */
import { useState } from "react";
import { Linking, StyleSheet, Text, View } from "react-native";
import { requestPrivacy, type MonitoringPolicy } from "../api";
import { locationRetentionDays } from "../config";
import type { LocationConsent } from "../consent";
import { clearQueryCache } from "../data/queryClient";
import { useSaveSetting, useServerSettings } from "../data/queries";
import { haptic } from "../haptics";
import { useT } from "../i18n";
import { readQueue } from "../offline";
import { setSettings, useSettings, type AppSettings } from "../settings";
import { Banner, Button } from "../ui/kit";
import { Rise } from "../ui/motion";
import { usePolicyPage } from "../ui/PolicyPage";
import { Row, Section, Segmented, ToggleRow } from "../ui/settings/rows";
import { Sheet } from "../ui/Sheet";
import { color, space } from "../ui/theme";
import { toast } from "../ui/toast";
import { currentAppVersion } from "../version";
import { Platform } from "react-native";

type Props = {
  visible: boolean;
  onClose: () => void;
  consent: LocationConsent;
  policy?: MonitoringPolicy | null;
  onReviewConsent: () => void;
  onWithdrawConsent: () => void;
  onSignOut: () => Promise<void>;
};

export function SettingsPage(p: Props) {
  return (
    <Sheet visible={p.visible} title="Settings" onClose={p.onClose} testID="page-settings">
      <SettingsBody {...p} />
    </Sheet>
  );
}

export function SettingsBody({
  consent,
  policy,
  onReviewConsent,
  onWithdrawConsent,
  onSignOut,
}: Props) {
  const s = useSettings();
  const t = useT();
  useServerSettings(); // pulls the server copy (cached); never overwrites a change made here
  const save = useSaveSetting();
  const policyPage = usePolicyPage();
  const [privacyOpen, setPrivacyOpen] = useState(false);
  const [privacyBusy, setPrivacyBusy] = useState(false);
  const [confirmOut, setConfirmOut] = useState<number | null>(null);
  const [signingOut, setSigningOut] = useState(false);
  const [confirmWithdraw, setConfirmWithdraw] = useState(false);

  const set = (patch: Partial<AppSettings>) => {
    setSettings(patch);
    save.mutate(patch);
  };

  const sendPrivacy = (kind: "access" | "correction" | "deletion") => {
    setPrivacyBusy(true);
    void requestPrivacy(kind)
      .then((r) => {
        haptic.success();
        setPrivacyOpen(false);
        toast.show(
          "success",
          "Request received",
          `Reference ${r.reference ?? "on file"} · answer within ${r.sla_days} days.`
        );
      })
      .catch(() =>
        toast.show(
          "danger",
          "Couldn't send",
          "Try again with signal, or email privacy@porterchain.com."
        )
      )
      .finally(() => setPrivacyBusy(false));
  };

  const iosOrAndroid = Platform.OS === "ios";
  const navOptions = [
    { value: "auto" as const, label: "Auto" },
    { value: "google" as const, label: "Google" },
    ...(iosOrAndroid ? [{ value: "apple" as const, label: "Apple" }] : []),
    { value: "waze" as const, label: "Waze" },
  ];

  return (
    <View style={st.wrap}>
      <Section title={t("driving").toUpperCase()} testID="settings-driving">
        <Segmented
          label={t("navApp")}
          options={navOptions}
          value={s.nav_app}
          onChange={(v) => set({ nav_app: v })}
          testID="set-nav"
        />
        <ToggleRow
          label={t("voice")}
          sub="Reads the next stop out loud in Drive mode"
          value={s.voice}
          onChange={(v) => set({ voice: v })}
          testID="set-voice"
        />
        <ToggleRow
          label={t("driveAuto")}
          sub="Opens Drive mode when you start moving to a stop"
          value={s.drive_mode_auto}
          onChange={(v) => set({ drive_mode_auto: v })}
          testID="set-drive-auto"
        />
        <Segmented
          label={t("batterySaver")}
          options={[
            { value: 0, label: "Off" },
            { value: 15, label: "15%" },
            { value: 20, label: "20%" },
            { value: 30, label: "30%" },
          ]}
          value={s.battery_saver_pct}
          onChange={(v) => set({ battery_saver_pct: v })}
          testID="set-battery"
        />
      </Section>

      <Section title={t("display").toUpperCase()}>
        <Segmented
          label={t("textSize")}
          options={[
            { value: 0.9, label: "A−" },
            { value: 1, label: "A" },
            { value: 1.15, label: "A+" },
            { value: 1.3, label: "A++" },
          ]}
          value={s.text_scale}
          onChange={(v) => set({ text_scale: v })}
          testID="set-text"
        />
        <ToggleRow
          label={t("haptics")}
          value={s.haptics}
          onChange={(v) => set({ haptics: v })}
          testID="set-haptics"
        />
        <Segmented
          label={t("language")}
          options={[
            { value: "en" as const, label: "English" },
            { value: "fr" as const, label: "Français" },
          ]}
          value={s.language}
          onChange={(v) => set({ language: v })}
          testID="set-lang"
        />
      </Section>

      <Section title={t("notifications").toUpperCase()}>
        <ToggleRow
          label={t("notifyJobs")}
          value={s.notify_jobs}
          onChange={(v) => set({ notify_jobs: v })}
        />
        <ToggleRow
          label={t("notifyRoute")}
          value={s.notify_route_changes}
          onChange={(v) => set({ notify_route_changes: v })}
        />
        <ToggleRow
          label={t("notifyMessages")}
          value={s.notify_messages}
          onChange={(v) => set({ notify_messages: v })}
        />
        <ToggleRow
          label={t("notifyDocs")}
          value={s.notify_documents}
          onChange={(v) => set({ notify_documents: v })}
        />
        <Row label="Phone notification settings" onPress={() => void Linking.openSettings()} />
      </Section>

      <Section title={t("privacy").toUpperCase()} testID="settings-privacy">
        <Row
          label="Background location"
          sub={
            consent
              ? `On while on duty · agreed ${new Date(consent.agreedAt).toLocaleDateString()}`
              : "Off · dispatch sees you only while the app is open"
          }
          value={consent ? "On" : "Off"}
          onPress={onReviewConsent}
          testID="set-consent"
        />
        <Row
          label="Electronic Monitoring Policy"
          value={policy ? `v${policy.version}` : undefined}
          onPress={() => policyPage.open(policy)}
          testID="set-policy"
        />
        <Row
          label="Location history"
          value={`${locationRetentionDays} days`}
          sub="Older points are deleted automatically"
        />
        {consent ? (
          confirmWithdraw ? (
            <Rise>
              <View style={st.inline}>
                <Banner
                  tone="warn"
                  title="Turn off background location?"
                  body="Dispatch won't see the van when the screen is locked."
                />
                <Button
                  tone="danger"
                  label="Turn off"
                  onPress={() => {
                    setConfirmWithdraw(false);
                    onWithdrawConsent();
                  }}
                />
                <Button tone="quiet" label="Keep it on" onPress={() => setConfirmWithdraw(false)} />
              </View>
            </Rise>
          ) : (
            <Row
              label="Withdraw location consent"
              tone="danger"
              onPress={() => setConfirmWithdraw(true)}
              testID="set-withdraw"
            />
          )
        ) : null}
        <Row
          label="My data (PIPEDA)"
          sub="Get a copy, fix something, or ask us to delete it"
          onPress={() => setPrivacyOpen((o) => !o)}
          testID="set-privacy"
        />
        {privacyOpen ? (
          <Rise>
            <View style={st.inline} testID="privacy-choices">
              <Button
                label="Send me a copy of my data"
                busy={privacyBusy}
                onPress={() => sendPrivacy("access")}
              />
              <Button
                label="Correct my information"
                disabled={privacyBusy}
                onPress={() => sendPrivacy("correction")}
              />
              <Button
                tone="quiet"
                label="Delete my account data"
                disabled={privacyBusy}
                onPress={() => sendPrivacy("deletion")}
              />
              <Text style={st.fine}>
                We answer within 30 days. Delivery records may be kept where the law requires.
              </Text>
            </View>
          </Rise>
        ) : null}
      </Section>

      <Section title={t("app").toUpperCase()}>
        <Row label="Version" value={currentAppVersion()} />
        <Row
          label={t("clearCache")}
          sub="Frees space; your unsynced work is kept"
          onPress={() =>
            void clearQueryCache().then(() =>
              toast.show("success", "Cache cleared", "Fresh data loads in the background.")
            )
          }
          testID="set-clear"
        />
        {confirmOut == null ? (
          <Row
            label={t("signOut")}
            tone="danger"
            onPress={() =>
              void readQueue().then(
                (q) => setConfirmOut(q.length),
                () => setConfirmOut(0)
              )
            }
            testID="sign-out"
          />
        ) : (
          <Rise>
            <View style={st.inline}>
              <Banner
                tone={confirmOut ? "danger" : "warn"}
                title={confirmOut ? "Unsynced work on this phone" : "Sign out?"}
                body={
                  confirmOut
                    ? `${confirmOut} saved action${confirmOut === 1 ? " hasn't" : "s haven't"} reached PorterChain yet. Signing out deletes ${confirmOut === 1 ? "it" : "them"}.`
                    : "This removes your data from this phone."
                }
              />
              <Button
                tone="danger"
                label={confirmOut ? "Sign out anyway" : t("signOut")}
                busy={signingOut}
                testID="sign-out-confirm"
                onPress={() => {
                  setSigningOut(true);
                  void onSignOut().finally(() => setSigningOut(false));
                }}
              />
              <Button tone="quiet" label="Cancel" onPress={() => setConfirmOut(null)} />
            </View>
          </Rise>
        )}
      </Section>
      {policyPage.page}
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { gap: space.lg },
  inline: { gap: space.sm, padding: space.md },
  fine: { fontSize: 13, lineHeight: 18, color: color.inkMuted },
});
