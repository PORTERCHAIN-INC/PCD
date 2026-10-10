import { useEffect, useState } from "react";
import { ScrollView, Text, View, StyleSheet } from "react-native";
import { colors, radius, spacing, typography } from "@porterchain/mobile-theme";
import {
  fetchPerformance,
  fetchProfile,
  fetchShift,
  sendEmergency,
  setAvailability,
  shiftBreak,
  shiftResume,
} from "../api";
import { fieldWarning, humanFieldCopy } from "../fieldCopy";
import { showMonitoringPolicy } from "../hooks/useComplianceGate";
import { clearSession } from "../session";
import { Card, CardTitle, Kpi } from "../ui/Card";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";
import { ScreenHeader } from "../ui/ScreenHeader";
import type { DriverPerformance, DriverProfile, Handshake, ShiftSnapshot } from "../types";

type Props = {
  handshake: Handshake;
  onOpenInbox: () => void;
  onOpenSupport: () => void;
  onSignedOut: () => void;
};

export function MoreScreen({ handshake, onOpenInbox, onOpenSupport, onSignedOut }: Props) {
  const [perf, setPerf] = useState<DriverPerformance | null>(null);
  const [shift, setShift] = useState<ShiftSnapshot | null>(null);
  const [profile, setProfile] = useState<DriverProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sos, setSos] = useState<string | null>(null);
  const [shiftMsg, setShiftMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [shiftBusy, setShiftBusy] = useState<"break" | "resume" | "mode" | null>(null);
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    void fetchPerformance()
      .then(setPerf)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "performance_failed");
      });
    void fetchShift()
      .then(setShift)
      .catch(() => {
        /* optional */
      });
    void fetchProfile()
      .then(setProfile)
      .catch(() => {
        /* optional */
      });
  }, []);

  const profileBlock = profile?.profile ?? profile;
  const profileName = profileBlock?.full_name || handshake.driverName || "—";
  const profileEmail = profileBlock?.email || "—";
  const profilePhone = profileBlock?.phone || "—";
  const profileStatus = (profileBlock?.status || "—").replace(/_/g, " ");

  const onDuty = Boolean(shift?.shift_active || handshake.online);
  const pushWarn = fieldWarning(handshake.push.detail);
  const locationWarn = fieldWarning(handshake.location.detail);

  return (
    <Screen includeBottomSafeArea={false}>
      <ScreenHeader title="More" lede="Inbox, support, shift controls, and account." />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
      >
        <Card>
          <CardTitle>Profile</CardTitle>
          <Text style={styles.body}>{profileName}</Text>
          <Text style={styles.meta}>{profileEmail}</Text>
          <Text style={styles.meta}>
            {profilePhone} · {profileStatus}
          </Text>
          <Text style={styles.meta}>Rating {profileBlock?.rating ?? perf?.rating ?? "—"}</Text>
        </Card>

        <Card>
          <CardTitle>Stay connected</CardTitle>
          <View style={styles.row}>
            <PrimaryButton label="Inbox" onPress={onOpenInbox} />
            <PrimaryButton tone="ghost" label="Support" onPress={onOpenSupport} />
          </View>
        </Card>

        <View style={styles.kpis}>
          <Kpi label="Score" value={perf ? String(perf.score) : "—"} />
          <Kpi label="On time" value={perf ? `${perf.on_time_percent}%` : "—"} />
        </View>
        <View style={styles.kpis}>
          <Kpi label="Completion" value={perf ? `${perf.completion_percent}%` : "—"} />
          <Kpi label="Acceptance" value={perf ? `${perf.acceptance_rate}%` : "—"} />
        </View>
        <Card>
          <CardTitle>This shift</CardTitle>
          <Text style={styles.body}>
            Mode {(shift?.availability || handshake.availability || "—").replace(/_/g, " ")}
            {shift?.on_break ? " · on break" : ""}
          </Text>
          <Text style={styles.body}>Deliveries today {perf?.deliveries_today ?? "—"}</Text>
          <Text style={styles.body}>Lifetime {perf?.deliveries_total ?? "—"}</Text>
          <Text style={styles.body}>Rating {perf?.rating ?? "—"}</Text>
          {pushWarn ? <Text style={styles.meta}>{pushWarn}</Text> : null}
          {locationWarn ? <Text style={styles.meta}>{locationWarn}</Text> : null}
          {!onDuty ? (
            <Text style={styles.meta}>
              Start shift from Work (30-second vehicle check) before Idle or Busy.
            </Text>
          ) : null}
          <View style={styles.row}>
            <PrimaryButton
              tone="ghost"
              label={shiftBusy === "break" ? "Starting break…" : "Take break"}
              disabled={Boolean(shiftBusy) || !handshake.online}
              onPress={() => {
                setShiftBusy("break");
                void shiftBreak()
                  .then(() => {
                    setShiftMsg("On break");
                    return fetchShift().then(setShift);
                  })
                  .catch((err: unknown) => {
                    setShiftMsg(err instanceof Error ? err.message : "break_failed");
                  })
                  .finally(() => setShiftBusy(null));
              }}
            />
            <PrimaryButton
              tone="ghost"
              label={shiftBusy === "resume" ? "Resuming…" : "Resume duty"}
              disabled={Boolean(shiftBusy) || !onDuty}
              onPress={() => {
                setShiftBusy("resume");
                void shiftResume()
                  .then(() => {
                    setShiftMsg("Back on duty");
                    return fetchShift().then(setShift);
                  })
                  .catch((err: unknown) => {
                    setShiftMsg(err instanceof Error ? err.message : "resume_failed");
                  })
                  .finally(() => setShiftBusy(null));
              }}
            />
          </View>
          <View style={styles.row}>
            <PrimaryButton
              tone="ghost"
              label="Idle"
              disabled={Boolean(shiftBusy) || !onDuty}
              onPress={() => {
                setShiftBusy("mode");
                void setAvailability("idle")
                  .then((next) => {
                    setShift(next);
                    setShiftMsg("Marked idle");
                  })
                  .catch((err: unknown) => {
                    setShiftMsg(
                      humanFieldCopy(err instanceof Error ? err.message : "availability_failed")
                    );
                  })
                  .finally(() => setShiftBusy(null));
              }}
            />
            <PrimaryButton
              tone="ghost"
              label="Busy"
              disabled={Boolean(shiftBusy) || !onDuty}
              onPress={() => {
                setShiftBusy("mode");
                void setAvailability("busy")
                  .then((next) => {
                    setShift(next);
                    setShiftMsg("Marked busy");
                  })
                  .catch((err: unknown) => {
                    setShiftMsg(
                      humanFieldCopy(err instanceof Error ? err.message : "availability_failed")
                    );
                  })
                  .finally(() => setShiftBusy(null));
              }}
            />
          </View>
          {shiftMsg ? <Text style={styles.meta}>{shiftMsg}</Text> : null}
        </Card>
        <Card>
          <CardTitle>Emergency</CardTitle>
          <Text style={styles.meta}>
            Alerts dispatch. Location is the last ping PorterChain received.
          </Text>
          <PrimaryButton
            tone="danger"
            label={busy ? "Sending…" : "Send SOS"}
            disabled={busy}
            onPress={() => {
              setBusy(true);
              void sendEmergency()
                .then(() => setSos("Dispatch notified"))
                .catch((err: unknown) => {
                  setSos(err instanceof Error ? err.message : "sos_failed");
                })
                .finally(() => setBusy(false));
            }}
          />
          {sos ? <Text style={styles.meta}>{sos}</Text> : null}
        </Card>
        <Card>
          <CardTitle>Account</CardTitle>
          <PrimaryButton
            tone="ghost"
            label="Electronic monitoring policy"
            onPress={showMonitoringPolicy}
          />
          <PrimaryButton
            tone="ghost"
            label={signingOut ? "Signing out…" : "Sign out"}
            disabled={signingOut}
            onPress={() => {
              setSigningOut(true);
              void clearSession()
                .then(() => onSignedOut())
                .catch((err: unknown) => {
                  setError(err instanceof Error ? err.message : "sign_out_failed");
                })
                .finally(() => setSigningOut(false));
            }}
          />
        </Card>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  error: { ...typography.caption, color: colors.danger },
  flex: { flex: 1 },
  list: { gap: spacing.md, paddingBottom: spacing.xl },
  kpis: {
    flexDirection: "row",
    gap: spacing.md,
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    padding: spacing.md,
  },
  body: { ...typography.body, color: colors.primary },
  meta: { ...typography.caption, color: colors.muted },
  row: { gap: spacing.sm, marginTop: spacing.sm },
});
