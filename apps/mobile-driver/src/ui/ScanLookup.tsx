/**
 * Scan anytime: scan any of YOUR parcel labels to see the box, its job and what you can
 * do next. Someone else's (or a forged) label shows "Not your parcel" and nothing else.
 */
import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { fetchJob, lookupLabel, type LabelLookup } from "../api";
import type { DriverJobDetail } from "../types";
import { StopDocumentsCard } from "./job/StopDocumentsCard";
import { scanFix, type ScanOutcome } from "../scanFeedback";
import { BarcodeScannerModal } from "./BarcodeScannerModal";
import { Banner, Body, Button } from "./kit";
import { Sheet } from "./Sheet";
import { color, space, type } from "./theme";

const ACTION_LABEL: Record<string, string> = {
  scan_pickup: "Scan at pickup",
  scan_delivery: "Scan at delivery",
  report_missing: "Report missing",
  note: "Add a note",
  photo: "Add a photo",
  exception: "Report a problem",
};

const STATUS_LABEL: Record<string, string> = {
  manifested: "Waiting for pickup",
  missing_at_pickup: "Reported missing",
  picked_up: "Picked up",
  loaded: "Loaded",
  out_for_delivery: "Out for delivery",
  delivered: "Delivered",
};

export function ScanLookupButton({
  currentOrderId,
  onOpenJob,
}: {
  currentOrderId?: string | null;
  onOpenJob: () => void;
}) {
  const [scanning, setScanning] = useState(false);
  const [found, setFound] = useState<LabelLookup | null>(null);
  const [notYours, setNotYours] = useState(false);
  const [job, setJob] = useState<DriverJobDetail | null>(null);
  const [jobErr, setJobErr] = useState(false);

  // Any of the driver's assigned jobs (the server already proved it's theirs).
  useEffect(() => {
    setJob(null);
    setJobErr(false);
    if (!found) return;
    let live = true;
    fetchJob(found.order.id)
      .then((j) => live && setJob(j))
      .catch(() => live && setJobErr(true));
    return () => {
      live = false;
    };
  }, [found]);

  async function onScan(code: string): Promise<ScanOutcome> {
    const meta = { ...((await scanFix()) ?? {}), scanned_at: new Date().toISOString() };
    try {
      const r = await lookupLabel(code, {
        ...meta,
        expected_order_id: currentOrderId ?? undefined,
      });
      setNotYours(false);
      setFound(r);
      return r.warning ? "warn" : "ok";
    } catch (e) {
      const m = e instanceof Error ? e.message : "";
      setFound(null);
      if (/not_yours|404/i.test(m)) {
        setNotYours(true);
        return "error";
      }
      throw e;
    }
  }

  const p = found?.parcel;
  return (
    <>
      <Button label="Scan a label" testID="scan-lookup" onPress={() => setScanning(true)} />
      <BarcodeScannerModal
        visible={scanning}
        title="Scan any of your labels"
        hint="See the box, its stop and what you can do next."
        onClose={() => setScanning(false)}
        onScan={onScan}
      />
      <Sheet
        visible={Boolean(found) || notYours}
        title={notYours ? "Not your parcel" : `Box ${p?.tracking_suffix ?? ""}`}
        kicker={found ? `Job ${found.order.order_number}` : undefined}
        tone={notYours || found?.warning ? "danger" : "default"}
        onClose={() => {
          setFound(null);
          setNotYours(false);
        }}
        testID="scan-lookup-sheet"
        footer={
          found && found.order.id === currentOrderId ? (
            <Button
              label="Open this job"
              tone="primary"
              onPress={() => {
                setFound(null);
                onOpenJob();
              }}
            />
          ) : undefined
        }
      >
        {notYours ? (
          <Body>
            This label isn't on any of your jobs. Leave the box where it is and tell dispatch.
          </Body>
        ) : found && p ? (
          <View style={styles.body}>
            {found.warning === "wrong_stop" ? (
              <Banner
                tone="warn"
                title="Different stop"
                body="This box is yours but belongs to another stop, not the one you're on."
              />
            ) : null}
            <Text style={styles.row}>{STATUS_LABEL[p.status] ?? p.status}</Text>
            {p.item_label ? <Text style={styles.row}>{p.item_label}</Text> : null}
            {p.box_count && p.box_count > 1 ? (
              <Text style={styles.muted}>
                Box {p.box_index} of {p.box_count}
              </Text>
            ) : p.total_parcels && p.total_parcels > 1 ? (
              <Text style={styles.muted}>
                Parcel {p.parcel_index} of {p.total_parcels}
              </Text>
            ) : null}
            {p.stop_sequence != null ? (
              <Text style={styles.muted}>Stop {p.stop_sequence}</Text>
            ) : null}
            <Text style={styles.muted}>
              You can: {found.allowed_actions.map((a) => ACTION_LABEL[a] ?? a).join(" · ")}
            </Text>
            {job ? (
              <View style={styles.job} testID="scan-lookup-job">
                {job.pickup_address ? (
                  <Text style={styles.muted}>Pickup: {job.pickup_address}</Text>
                ) : null}
                {job.delivery_address ? (
                  <Text style={styles.muted}>Drop-off: {job.delivery_address}</Text>
                ) : null}
                {job.special_instructions ? (
                  <Text style={styles.muted}>Notes: {job.special_instructions}</Text>
                ) : null}
                {found.order.id !== currentOrderId ? (
                  <Text style={styles.muted}>
                    Not your current stop. Finish the current job first; this one is in your list.
                  </Text>
                ) : null}
                <StopDocumentsCard orderId={found.order.id} />
              </View>
            ) : jobErr ? (
              <Text style={styles.muted}>
                Couldn't load the job details. Pull to refresh Today.
              </Text>
            ) : null}
          </View>
        ) : null}
      </Sheet>
    </>
  );
}

const styles = StyleSheet.create({
  body: { gap: space.sm },
  row: { ...type.bodyStrong, color: color.ink },
  muted: { ...type.small, color: color.inkMuted },
  job: { gap: space.xs, marginTop: space.sm },
});
