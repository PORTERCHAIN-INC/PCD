import { useCallback, useEffect, useRef, useState } from "react";
import { ScrollView, Text, View, StyleSheet } from "react-native";
import { colors, spacing, typography } from "@porterchain/mobile-theme";
import {
  acceptOrder,
  fetchJobs,
  fetchJobsHistory,
  optimizeAccept,
  optimizeJobs,
  optimizeRunStatus,
  optimizeUndo,
  rejectOrder,
} from "../api";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";
import { Card, CardTitle } from "../ui/Card";
import type { DriverJobSummary, OptimizeResult } from "../types";

type Props = {
  currentOrderId: string | null;
  onOpenWork: () => void;
  onOpenJob: (orderId: string) => void;
  /** Refresh route/nav geometry after Accept or Undo. */
  onSequenceApplied?: () => void;
};

const POLL_MS = 2500;
const POLL_MAX = 24;

function deltaNote(result: OptimizeResult, applied: boolean): string {
  const m = (result.metrics || {}) as Record<string, unknown>;
  const parts: string[] = [applied ? "Route applied" : "Preview ready"];
  if (typeof m.fuel_delta_cents === "number" && m.fuel_delta_cents !== 0) {
    const dollars = (Math.abs(m.fuel_delta_cents as number) / 100).toFixed(2);
    parts.push(
      (m.fuel_delta_cents as number) > 0 ? `saves ~$${dollars} fuel` : `~$${dollars} more fuel`
    );
  } else if (typeof m.estimated_fuel_cents === "number") {
    parts.push(`est. fuel $${((m.estimated_fuel_cents as number) / 100).toFixed(2)}`);
  }
  if (typeof m.after_distance_km === "number") {
    parts.push(`${m.after_distance_km} km`);
  }
  return parts.join(" · ");
}

export function JobsScreen({ currentOrderId, onOpenWork, onOpenJob, onSequenceApplied }: Props) {
  const [jobs, setJobs] = useState<DriverJobSummary[]>([]);
  const [history, setHistory] = useState<DriverJobSummary[]>([]);
  const [current, setCurrent] = useState<DriverJobSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [preview, setPreview] = useState<OptimizeResult | null>(null);
  const [canUndo, setCanUndo] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearPoll = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const load = useCallback(async () => {
    setError(null);
    try {
      const [data, hist] = await Promise.all([
        fetchJobs(),
        fetchJobsHistory().catch(() => ({ history: [] as DriverJobSummary[] })),
      ]);
      setCurrent(data.current ?? null);
      const rest = [...(data.upcoming ?? []), ...(data.completed ?? [])];
      const seen = new Set(rest.map((job) => job.order_id));
      if (data.current && !seen.has(data.current.order_id)) rest.unshift(data.current);
      setJobs(data.jobs?.length ? data.jobs : rest);
      setHistory(hist.history ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "jobs_failed");
    }
  }, []);

  useEffect(() => {
    void load();
    return () => clearPoll();
  }, [load]);

  async function run(id: string, work: () => Promise<unknown>) {
    setBusy(id);
    try {
      await work();
      await load();
      onOpenWork();
    } catch (err) {
      setError(err instanceof Error ? err.message : "action_failed");
    } finally {
      setBusy(null);
    }
  }

  async function runOptimize() {
    setBusy("optimize");
    setNote("Building preview…");
    setError(null);
    setPreview(null);
    clearPoll();
    try {
      // Online: Preview→Accept. Network failure only: queue auto-apply on reconnect.
      let result = await optimizeJobs();
      const runId = result.run_id;
      if (runId && (result.status === "pending" || !result.status)) {
        let polls = 0;
        await new Promise<void>((resolve) => {
          pollRef.current = setInterval(() => {
            void optimizeRunStatus(runId)
              .then((status) => {
                polls += 1;
                const st = status.status || "pending";
                if (st === "ready") {
                  clearPoll();
                  setPreview(status);
                  setNote(deltaNote(status, false));
                  resolve();
                } else if (st === "error") {
                  clearPoll();
                  setNote(status.message || "Optimize failed");
                  resolve();
                } else if (polls >= POLL_MAX) {
                  clearPoll();
                  setNote("Preview timed out — try again.");
                  resolve();
                } else {
                  setNote(`Optimize ${st}`);
                }
              })
              .catch((err) => {
                clearPoll();
                setError(err instanceof Error ? err.message : "optimize_failed");
                resolve();
              });
          }, POLL_MS);
        });
      } else if (result.status === "ready") {
        setPreview(result);
        setNote(deltaNote(result, false));
      } else if (result.status === "error") {
        setNote(result.message || "Optimize failed");
      } else {
        setNote(result.message || `Optimize ${result.status || "queued"}`);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "optimize_failed";
      const networky = /network|fetch|timeout|offline|Failed to fetch|Network request failed/i.test(
        msg
      );
      if (networky) {
        const { enqueueOfflineAction } = await import("../offline");
        await enqueueOfflineAction("optimize_route", { preview: false });
        setNote("Optimize queued — will run when online.");
        setPreview(null);
      } else {
        setError(
          msg.includes("sequence_version_conflict")
            ? "Stop order conflict — refresh and try again."
            : msg
        );
      }
    } finally {
      setBusy(null);
    }
  }

  async function acceptPreview() {
    if (!preview?.run_id) return;
    setBusy("accept");
    setError(null);
    try {
      const result = await optimizeAccept(preview.run_id, preview.sequence_version);
      setPreview(null);
      setCanUndo(true);
      setNote(deltaNote(result, true));
      await load();
      onSequenceApplied?.();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "accept_failed";
      setError(
        msg.includes("sequence_version_conflict")
          ? "Stop order conflict — request a new preview."
          : msg
      );
    } finally {
      setBusy(null);
    }
  }

  async function undoLast() {
    setBusy("undo");
    setError(null);
    try {
      const result = await optimizeUndo();
      if (result.error === "nothing_to_undo" || result.ok === false) {
        setNote(result.message || "Nothing to undo");
        setCanUndo(false);
        return;
      }
      setCanUndo(false);
      setPreview(null);
      setNote(result.message || "Previous stop order restored.");
      await load();
      onSequenceApplied?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "undo_failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Screen testID="mobile-jobs">
      <Text style={styles.title}>Jobs</Text>
      <Text style={styles.lede}>
        Assigned work from Porterchain. Preview stop order, then Accept — Fleetbase stays SoT.
      </Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {note ? <Text style={styles.note}>{note}</Text> : null}
      <View style={styles.actions}>
        {!preview ? (
          <PrimaryButton
            tone="ghost"
            label={busy === "optimize" ? "Building…" : "Optimize route"}
            disabled={Boolean(busy)}
            onPress={() => void runOptimize()}
          />
        ) : null}
        {preview ? (
          <>
            <PrimaryButton
              label={busy === "accept" ? "Applying…" : "Accept new order"}
              disabled={Boolean(busy)}
              onPress={() => void acceptPreview()}
            />
            <PrimaryButton
              tone="ghost"
              label="Keep current"
              disabled={Boolean(busy)}
              onPress={() => {
                setPreview(null);
                setNote("Kept current stop order.");
              }}
            />
          </>
        ) : null}
        {canUndo && !preview ? (
          <PrimaryButton
            tone="ghost"
            label={busy === "undo" ? "Undoing…" : "Undo last apply"}
            disabled={Boolean(busy)}
            onPress={() => void undoLast()}
          />
        ) : null}
        <PrimaryButton
          tone="ghost"
          label="Refresh"
          disabled={Boolean(busy)}
          onPress={() => void load()}
        />
      </View>
      {preview?.optimized_stops && preview.optimized_stops.length > 0 ? (
        <Card>
          <CardTitle>Preview sequence</CardTitle>
          {preview.optimized_stops.slice(0, 12).map((stop, i) => (
            <Text key={`${String(stop.order_id)}-${i}`} style={styles.meta}>
              {i + 1}. {String(stop.stop_type || stop.type || "stop")} ·{" "}
              {String(stop.order_id || "—")}
            </Text>
          ))}
        </Card>
      ) : null}
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
      >
        {jobs.length === 0 ? <Text style={styles.empty}>No jobs on this shift yet.</Text> : null}
        {jobs.map((job) => {
          const active = job.order_id === (current?.order_id ?? currentOrderId);
          return (
            <Card key={job.order_id} style={active ? styles.active : undefined}>
              <Text style={styles.jobNo}>{job.order_number}</Text>
              <Text style={styles.meta}>{job.tracking_number}</Text>
              <Text style={styles.addr}>{job.pickup_address || "Pickup —"}</Text>
              <Text style={styles.addr}>{job.delivery_address || "Dropoff —"}</Text>
              <Text style={styles.meta}>
                {(job.status || job.state || "assigned").replace(/_/g, " ")}
                {job.urgency && job.urgency !== "normal" ? ` · ${job.urgency}` : ""}
              </Text>
              <View style={styles.row}>
                <PrimaryButton
                  tone="ghost"
                  label="Open"
                  disabled={Boolean(busy)}
                  onPress={() => onOpenJob(job.order_id)}
                />
                {!active ? (
                  <PrimaryButton
                    label={busy === job.order_id ? "Accepting…" : "Accept"}
                    disabled={Boolean(busy)}
                    onPress={() => void run(job.order_id, () => acceptOrder(job.order_id))}
                  />
                ) : null}
                {!active ? (
                  <PrimaryButton
                    tone="ghost"
                    label="Decline"
                    disabled={Boolean(busy)}
                    onPress={() => void run(job.order_id, () => rejectOrder(job.order_id))}
                  />
                ) : null}
              </View>
            </Card>
          );
        })}

        <Card>
          <CardTitle>History</CardTitle>
          {history.slice(0, 12).map((job) => (
            <View key={`h-${job.order_id}`} style={styles.histRow}>
              <Text style={styles.addr}>{job.order_number}</Text>
              <Text style={styles.meta}>
                {(job.status || job.state || "done").replace(/_/g, " ")}
              </Text>
            </View>
          ))}
          {history.length === 0 ? <Text style={styles.empty}>No completed jobs yet.</Text> : null}
        </Card>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { ...typography.title, fontSize: 28, color: colors.primary },
  lede: { ...typography.caption, color: colors.muted, marginBottom: spacing.sm },
  error: { ...typography.caption, color: colors.danger },
  note: { ...typography.caption, color: colors.primary, marginBottom: spacing.sm },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginBottom: spacing.md },
  empty: { ...typography.body, color: colors.muted },
  flex: { flex: 1 },
  list: { gap: spacing.md, paddingBottom: spacing.xl },
  active: { borderWidth: 1.5, borderColor: colors.driverGreen },
  jobNo: { ...typography.title, color: colors.primary },
  addr: { ...typography.body, color: colors.primary },
  meta: { ...typography.caption, color: colors.muted },
  row: { gap: spacing.sm },
  histRow: { marginTop: spacing.sm },
});
