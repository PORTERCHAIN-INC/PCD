import { useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { emptyPretrip, PRETRIP_ITEMS, pretripComplete, type PretripChecks } from "../pretrip";
import { isClosed, needsAccept, normState } from "../stop/stopFlow";
import type { FieldSession } from "../hooks/useFieldSession";
import type { DriverJobSummary } from "../types";
import {
  Banner,
  Body,
  Button,
  Card,
  EmptyState,
  Heading,
  Label,
  Muted,
  Screen,
  Strong,
  Title,
} from "../ui/kit";
import { SyncBanners } from "../ui/SyncBanners";
import { color, radius, space, target, type } from "../ui/theme";

type Props = {
  field: FieldSession;
  action: string | null;
  onOpenJob: () => void;
  onGoOnDuty: (pretrip: PretripChecks) => void;
  onGoOffDuty: () => void;
  onSync: () => void;
};

const STATE_COPY: Record<string, string> = {
  DRIVER_ASSIGNED: "New — accept or decline",
  DRIVER_ACCEPTED: "Accepted · go to pickup",
  DRIVER_EN_ROUTE: "Going to pickup",
  AT_PICKUP: "At pickup",
  PICKED_UP: "Picked up · go to drop-off",
  IN_TRANSIT: "Going to drop-off",
  AT_DESTINATION: "At drop-off",
  DELIVERED: "Delivered",
  COMPLETED: "Done",
};

function jobStatus(job: DriverJobSummary): string {
  const s = normState(job.state ?? job.status);
  return STATE_COPY[s] ?? s.replace(/_/g, " ").toLowerCase();
}

export function TodayScreen({ field, action, onOpenJob, onGoOnDuty, onGoOffDuty, onSync }: Props) {
  const { handshake: h, busy, pending, rejected, refresh, setError } = field;
  const [pretrip, setPretrip] = useState<PretripChecks>(emptyPretrip());
  const onDuty = Boolean(h.online);
  const open = h.jobs.filter((j) => !isClosed(j.state ?? j.status));
  const done = h.stopsDone ?? 0;
  const total = h.stopsTotal ?? 0;
  const hasWork = Boolean(h.currentOrderId);
  const ready = pretripComplete(pretrip);

  const footer = !onDuty ? (
    <Button
      tone="primary"
      testID="go-on-duty"
      label={
        ready
          ? "Go on duty"
          : `Vehicle check ${PRETRIP_ITEMS.filter((i) => pretrip[i.id]).length}/${PRETRIP_ITEMS.length}`
      }
      hint="Starts your shift and shares your location with dispatch"
      busy={action === "duty"}
      disabled={!ready || h.auth !== "up"}
      onPress={() => onGoOnDuty(pretrip)}
    />
  ) : hasWork ? (
    <Button
      tone="primary"
      testID="open-job"
      label={needsAccept(h.currentOrderState) ? "New job — review" : "Open current job"}
      onPress={onOpenJob}
    />
  ) : (
    <Button
      label="Go off duty"
      testID="go-off-duty"
      busy={action === "duty"}
      onPress={onGoOffDuty}
    />
  );

  return (
    <Screen
      testID="mobile-track"
      footer={footer}
      onRefresh={() => void refresh()}
      refreshing={busy}
    >
      <View style={styles.head}>
        <Title>{h.driverName ? `Hi, ${h.driverName.split(" ")[0]}` : "Today"}</Title>
        <View
          style={[styles.pill, onDuty ? styles.pillOn : styles.pillOff]}
          accessibilityLabel={onDuty ? "You are on duty" : "You are off duty"}
        >
          <Strong style={onDuty ? styles.pillTextOn : undefined}>
            {onDuty ? "On duty" : "Off duty"}
          </Strong>
        </View>
      </View>

      <SyncBanners
        offline={h.api === "down"}
        pending={pending}
        rejected={rejected}
        error={h.error}
        onSync={onSync}
        onDismissError={() => setError(null)}
      />

      {!onDuty ? (
        <Card testID="pretrip-check">
          <Heading>Vehicle check</Heading>
          <Muted>Tap each one when it's OK. Takes 30 seconds.</Muted>
          {PRETRIP_ITEMS.map((item) => {
            const on = pretrip[item.id];
            return (
              <Pressable
                key={item.id}
                accessibilityRole="checkbox"
                accessibilityState={{ checked: on }}
                accessibilityLabel={item.label}
                onPress={() => setPretrip({ ...pretrip, [item.id]: !on })}
                style={[styles.check, on && styles.checkOn]}
                testID={`pretrip-${item.id}`}
              >
                <View style={[styles.box, on && styles.boxOn]}>
                  {on ? <Strong style={styles.tick}>✓</Strong> : null}
                </View>
                <Body>{item.label}</Body>
              </Pressable>
            );
          })}
        </Card>
      ) : (
        <Card testID="today-progress">
          <Label>Today</Label>
          <Title>
            {done} of {total} stops done
          </Title>
          <View
            style={styles.bar}
            accessibilityRole="progressbar"
            accessibilityValue={{ min: 0, max: total || 1, now: done }}
          >
            <View
              style={[
                styles.barFill,
                { width: `${total ? Math.min(100, (done / total) * 100) : 0}%` },
              ]}
            />
          </View>
          {h.nextStop ? (
            <Body>
              Next: <Strong>{h.nextStop}</Strong>
              {h.etaLabel ? ` · ${h.etaLabel}` : ""}
            </Body>
          ) : null}
        </Card>
      )}

      {onDuty && (h.location.kind === "denied" || h.location.kind === "error") ? (
        <Banner tone="warn" title="Location is off" body={h.location.detail} />
      ) : null}

      <Label>Jobs today</Label>
      {open.length === 0 ? (
        <EmptyState
          testID="today-empty"
          title="No jobs yet"
          body={
            onDuty
              ? "Stay on duty. You'll get a notification when dispatch sends a job."
              : "Go on duty to receive jobs."
          }
        />
      ) : (
        open.map((job) => {
          const current = job.order_id === h.currentOrderId;
          return (
            <Pressable
              key={job.order_id}
              accessibilityRole={current ? "button" : "text"}
              accessibilityLabel={`Job ${job.order_number}. ${jobStatus(job)}. From ${job.pickup_address ?? "pickup"} to ${job.delivery_address ?? "drop-off"}`}
              disabled={!current}
              onPress={onOpenJob}
              style={[styles.job, current && styles.jobCurrent]}
              testID={`job-${job.order_id}`}
            >
              <View style={styles.jobHead}>
                <Strong>#{job.order_number}</Strong>
                {current ? <Label style={styles.now}>NOW</Label> : null}
              </View>
              <Muted>{jobStatus(job)}</Muted>
              {job.pickup_address ? <Body numberOfLines={1}>↑ {job.pickup_address}</Body> : null}
              {job.delivery_address ? (
                <Body numberOfLines={1}>↓ {job.delivery_address}</Body>
              ) : null}
            </Pressable>
          );
        })
      )}
      {onDuty && hasWork ? (
        <Button tone="quiet" label="Go off duty" busy={action === "duty"} onPress={onGoOffDuty} />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  head: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: space.sm,
  },
  pill: {
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
    borderRadius: radius.pill,
    borderWidth: 2,
  },
  pillOn: { backgroundColor: color.primary, borderColor: color.primary },
  pillOff: { backgroundColor: color.surface, borderColor: color.ink },
  pillTextOn: { color: color.onPrimary },
  check: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    minHeight: target.min,
    paddingHorizontal: space.sm,
    borderRadius: radius.md,
  },
  checkOn: { backgroundColor: color.successSoft },
  box: {
    width: 32,
    height: 32,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: color.ink,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: color.surface,
  },
  boxOn: { backgroundColor: color.primary, borderColor: color.primary },
  tick: { color: color.onPrimary },
  bar: { height: 12, borderRadius: 6, backgroundColor: color.disabled, overflow: "hidden" },
  barFill: { height: 12, backgroundColor: color.primary },
  job: {
    backgroundColor: color.surface,
    borderRadius: radius.lg,
    padding: space.lg,
    gap: space.xs,
    borderWidth: 2,
    borderColor: "transparent",
  },
  jobCurrent: { borderColor: color.primary },
  jobHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  now: { color: color.primary, ...type.label },
});
