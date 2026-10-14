/**
 * Me: a compact hub. Everything renders from the cache instantly; details live on full-screen
 * pages (Documents, Settings) so this screen stays one glance.
 */
import { useState } from "react";
import { Image, Linking, StyleSheet, Text, View } from "react-native";
import { dispatchEmail, dispatchPhone, driverPortalUrl } from "../config";
import type { MonitoringPolicy } from "../api";
import type { LocationConsent } from "../consent";
import {
  useDocuments,
  useEarnings,
  useInbox,
  useMyProfile,
  useSchedule,
  useSupportHub,
  useVehicle,
} from "../data/queries";
import { PressScale } from "../ui/motion";
import { docAlerts } from "../docs";
import { moneyShort } from "../smart/geo";
import { useT } from "../i18n";
import type { FieldSession } from "../hooks/useFieldSession";
import { Banner, Button, Muted, Screen, Title } from "../ui/kit";
import { Row, Section } from "../ui/settings/rows";
import { useSos } from "../ui/SosButton";
import { color, space } from "../ui/theme";
import { UpdatedAgo } from "../ui/UpdatedAgo";
import { DocumentsPage } from "./DocumentsPage";
import { SettingsPage } from "./SettingsPage";
import { AvailabilityPage } from "./AvailabilityPage";
import { HelpPage } from "./HelpPage";
import { InboxPage } from "./InboxPage";
import { PayPage } from "./PayPage";
import { ProfilePage } from "./ProfilePage";

type Page = null | "settings" | "documents" | "profile" | "pay" | "availability" | "inbox" | "help";

type Props = {
  field: FieldSession;
  consent: LocationConsent;
  policy?: MonitoringPolicy | null;
  onReviewConsent: () => void;
  onWithdrawConsent: () => void;
  onSync: () => void;
  onSignOut: () => Promise<void>;
  /** Harness/deep link: open a page straight away. */
  initialPage?: Page;
};

export function MeScreen(props: Props) {
  const { field, onSync } = props;
  const { handshake: h, pending } = field;
  const t = useT();
  const [page, setPage] = useState<Page>(props.initialPage ?? null);
  const profile = useMyProfile();
  const inbox = useInbox();
  const sched = useSchedule();
  const hub = useSupportHub();
  const docs = useDocuments();
  const vehicle = useVehicle();
  const earnings = useEarnings();
  const { state: sos, ask: sendSos, page: sosPage } = useSos();
  const phone = hub.data?.emergency_contact?.ops_hotline ?? dispatchPhone;
  const email = hub.data?.emergency_contact?.ops_email ?? dispatchEmail;
  const alerts = docAlerts(docs.data?.documents, Date.now());
  const v = vehicle.data?.vehicle;
  const vLine = v
    ? [v.year, v.make, v.model].filter(Boolean).join(" ") +
      (v.plate || v.license_plate ? ` · ${v.plate ?? v.license_plate}` : "")
    : undefined;
  const e = earnings.data;

  return (
    <Screen testID="screen-me">
      <View style={st.head}>
        <PressScale
          accessibilityRole="button"
          accessibilityLabel="Open profile"
          onPress={() => setPage("profile")}
          style={st.who}
          testID="me-profile"
        >
          {profile.data?.photo_url ? (
            <Image source={{ uri: profile.data.photo_url }} style={st.avatar} />
          ) : (
            <View style={[st.avatar, st.avatarEmpty]}>
              <Text style={st.initials}>
                {(profile.data?.full_name ?? h.driverName ?? "?")
                  .split(/\s+/)
                  .map((w) => w[0])
                  .slice(0, 2)
                  .join("")
                  .toUpperCase()}
              </Text>
            </View>
          )}
          <View style={st.flex}>
            <Title numberOfLines={1}>{profile.data?.full_name ?? h.driverName ?? t("me")}</Title>
            <Muted>{h.online ? "On duty" : "Off duty"} · View profile ›</Muted>
          </View>
        </PressScale>
        <UpdatedAgo at={field.updatedAt} fetching={field.busy} offline={h.api === "down"} />
      </View>

      {h.push.kind === "denied" ? (
        <Banner
          tone="warn"
          title="Job alerts are off"
          body="Turn on notifications for PorterChain Driver, or you will miss new jobs."
          action={{ label: "Open phone settings", onPress: () => void Linking.openSettings() }}
        />
      ) : null}
      {alerts ? (
        <Banner
          tone="warn"
          title={`${alerts} document${alerts === 1 ? " needs" : "s need"} attention`}
          body="Expired or missing papers can stop new jobs."
          action={{ label: "Open documents", onPress: () => setPage("documents") }}
        />
      ) : null}

      {e && (e.today_cents != null || e.week_cents != null) ? (
        <View style={st.stats} testID="me-earnings">
          <Stat label="Today" value={moneyShort(e.today_cents ?? 0)} />
          <Stat label="This week" value={moneyShort(e.week_cents ?? 0)} />
          <Stat label="Month" value={moneyShort(e.month_cents ?? 0)} />
        </View>
      ) : null}

      <Section title="WORK">
        <Row
          label="Pay & time"
          sub="Earnings, statements, payouts, timesheets"
          onPress={() => setPage("pay")}
          testID="me-pay"
        />
        <Row
          label="Availability"
          value={sched.data ? `${sched.data.weekly_hours} h/wk` : undefined}
          sub="Days and hours dispatch can plan you"
          onPress={() => setPage("availability")}
          testID="me-availability"
        />
        <Row
          label="Notifications"
          badge={inbox.data?.unread_count || undefined}
          onPress={() => setPage("inbox")}
          testID="me-inbox"
        />
      </Section>

      <Section title="ACCOUNT">
        <Row
          label="Profile & security"
          sub="Name, address, emergency contact, email, phone, password"
          onPress={() => setPage("profile")}
          testID="me-profile-row"
        />
        <Row
          label={t("documents")}
          sub={docs.data ? (alerts ? "Action needed" : "All in order") : undefined}
          badge={alerts}
          onPress={() => setPage("documents")}
          testID="me-documents"
        />
        <Row
          label={t("vehicle")}
          value={vLine}
          onPress={() => setPage("documents")}
          testID="me-vehicle"
        />
        <Row
          label={t("settings")}
          sub="Language, navigation, voice, notifications, privacy, legal"
          onPress={() => setPage("settings")}
          testID="me-settings"
        />
        <Row
          label="Help"
          sub="Dispatch, tickets"
          onPress={() => setPage("help")}
          testID="me-help"
        />
      </Section>

      <Section title="DISPATCH" testID="me-dispatch">
        {phone ? (
          <Row
            label="Call dispatch"
            value={phone}
            tone="accent"
            onPress={() => void Linking.openURL(`tel:${phone}`)}
          />
        ) : null}
        <Row
          label="Email dispatch"
          value={email}
          onPress={() => void Linking.openURL(`mailto:${email}`)}
        />
        {pending ? (
          <Row
            label="Sync now"
            sub={`${pending} action${pending === 1 ? "" : "s"} waiting`}
            onPress={onSync}
            testID="me-sync"
          />
        ) : null}
      </Section>

      <Button
        tone="danger"
        label="SOS — emergency"
        testID="sos"
        busy={sos === "sending"}
        onPress={sendSos}
      />
      {sos === "failed" ? (
        <Banner
          tone="danger"
          title="SOS did not send"
          body="No connection. Call dispatch or 911."
          action={{ label: "Call 911", onPress: () => void Linking.openURL("tel:911") }}
        />
      ) : null}

      {sosPage}
      <DocumentsPage visible={page === "documents"} onClose={() => setPage(null)} />
      <ProfilePage
        visible={page === "profile"}
        onClose={() => setPage(null)}
        onSignOut={props.onSignOut}
      />
      <PayPage visible={page === "pay"} onClose={() => setPage(null)} />
      <AvailabilityPage visible={page === "availability"} onClose={() => setPage(null)} />
      <InboxPage visible={page === "inbox"} onClose={() => setPage(null)} />
      <HelpPage visible={page === "help"} onClose={() => setPage(null)} />
      <SettingsPage
        visible={page === "settings"}
        onClose={() => setPage(null)}
        consent={props.consent}
        policy={props.policy}
        onReviewConsent={() => {
          setPage(null);
          props.onReviewConsent();
        }}
        onWithdrawConsent={props.onWithdrawConsent}
        onSignOut={props.onSignOut}
      />
    </Screen>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View style={st.stat}>
      <Text style={st.statV} numberOfLines={1} adjustsFontSizeToFit>
        {value}
      </Text>
      <Text style={st.statL}>{label}</Text>
    </View>
  );
}

const st = StyleSheet.create({
  head: { flexDirection: "row", alignItems: "flex-end", gap: space.md },
  who: { flex: 1, flexDirection: "row", alignItems: "center", gap: space.md },
  avatar: { width: 56, height: 56, borderRadius: 28, borderWidth: 2, borderColor: color.primary },
  avatarEmpty: { backgroundColor: color.surface2, alignItems: "center", justifyContent: "center" },
  initials: { fontSize: 20, fontWeight: "900", color: color.ink },
  flex: { flex: 1 },
  stats: { flexDirection: "row", gap: space.sm },
  stat: {
    flex: 1,
    backgroundColor: color.surface,
    borderRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: color.border,
    padding: space.md,
  },
  statV: { fontSize: 20, fontWeight: "900", color: color.ink, fontVariant: ["tabular-nums"] },
  statL: { fontSize: 12, fontWeight: "700", color: color.inkMuted, marginTop: 2 },
});
