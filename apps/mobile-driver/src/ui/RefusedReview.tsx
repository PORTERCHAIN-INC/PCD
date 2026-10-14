/** Full-screen review of refused actions: what, where, when, why — Retry or Discard each. */
import { useCallback, useEffect, useState } from "react";
import { Alert, Modal, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import {
  discardRefused,
  loadRefused,
  notifyRefusedChanged,
  onOpenRefusedReview,
  retryRefused,
  type RefusedItem,
} from "../refusedReview";
import { Banner, Button } from "./kit";
import { color, radius, space, type } from "./theme";

function when(at: string | null): string {
  if (!at) return "Time unknown";
  const d = new Date(at);
  return Number.isNaN(d.getTime())
    ? at
    : d.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
}

export function RefusedReviewHost() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<RefusedItem[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<Record<string, string>>({});

  const reload = useCallback(async () => setItems(await loadRefused()), []);
  useEffect(
    () =>
      onOpenRefusedReview(() => {
        setOpen(true);
        setItems(null);
        setNote({});
        void reload();
      }),
    [reload]
  );

  const retry = async (it: RefusedItem) => {
    setBusy(it.key);
    try {
      const err = await retryRefused(it);
      setNote((n) => ({ ...n, [it.key]: err ? `Still refused: ${err}` : "Sent." }));
    } catch (e) {
      setNote((n) => ({ ...n, [it.key]: e instanceof Error ? e.message : "Retry failed" }));
    } finally {
      setBusy(null);
      notifyRefusedChanged();
      await reload();
    }
  };

  const discard = (it: RefusedItem) =>
    Alert.alert(
      "Discard this action?",
      `${it.action}${it.where ? ` (${it.where})` : ""} will not be sent. Tell dispatch if the stop still needs fixing.`,
      [
        { text: "Keep", style: "cancel" },
        {
          text: "Discard",
          style: "destructive",
          onPress: async () => {
            setBusy(it.key);
            try {
              await discardRefused(it);
            } finally {
              setBusy(null);
              notifyRefusedChanged();
              await reload();
            }
          },
        },
      ]
    );

  return (
    <Modal
      visible={open}
      animationType="slide"
      presentationStyle="fullScreen"
      onRequestClose={() => setOpen(false)}
    >
      <SafeAreaProvider>
        <SafeAreaView style={s.root} edges={["top", "bottom"]} testID="refused-review">
          <View style={s.head}>
            <Text style={s.title}>Refused actions</Text>
            <Button
              label="Done"
              tone="quiet"
              onPress={() => setOpen(false)}
              testID="refused-done"
            />
          </View>
          <Text style={s.sub}>
            The server did not accept these. Retry if you think it was a glitch. Discard if the job
            has moved on — dispatch can fix the stop.
          </Text>
          <ScrollView contentContainerStyle={{ gap: space.md, paddingBottom: space.xxl }}>
            {items === null ? <Text style={s.sub}>Loading…</Text> : null}
            {items?.length === 0 ? (
              <Banner tone="success" title="Nothing refused. All synced." />
            ) : null}
            {items?.map((it) => (
              <View key={it.key} style={s.card} testID="refused-item">
                <Text style={s.action}>{it.action}</Text>
                <Text style={s.meta}>
                  {[
                    it.where,
                    when(it.at),
                    it.source === "device" ? "Saved on this phone" : "On server",
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </Text>
                <Text style={s.reason}>{it.reason}</Text>
                {note[it.key] ? <Text style={s.meta}>{note[it.key]}</Text> : null}
                <View style={s.row}>
                  <View style={{ flex: 1 }}>
                    <Button
                      label="Retry"
                      tone="primary"
                      busy={busy === it.key}
                      disabled={busy != null}
                      onPress={() => void retry(it)}
                    />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Button
                      label="Discard"
                      tone="danger"
                      disabled={busy != null}
                      onPress={() => discard(it)}
                    />
                  </View>
                </View>
              </View>
            ))}
          </ScrollView>
        </SafeAreaView>
      </SafeAreaProvider>
    </Modal>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.bg, paddingHorizontal: space.lg },
  head: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: space.md,
  },
  title: { ...type.title, color: color.ink },
  sub: { ...type.body, color: color.inkMuted, marginBottom: space.md },
  card: {
    backgroundColor: color.surface,
    borderRadius: radius.lg,
    padding: space.lg,
    gap: space.xs,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: color.border,
  },
  action: { ...type.heading, color: color.ink },
  meta: { fontSize: 15, color: color.inkMuted },
  reason: { fontSize: 16, color: color.danger, marginTop: space.xs },
  row: { flexDirection: "row", gap: space.md, marginTop: space.md },
});
