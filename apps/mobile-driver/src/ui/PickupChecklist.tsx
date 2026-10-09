import { useCallback, useEffect, useState } from "react";
import { Text, View, StyleSheet } from "react-native";
import { colors, radius, spacing, typography } from "@porterchain/mobile-theme";
import { fetchPickupChecklist, reportPackageMissing } from "../api";
import { capturePodPhotoDataUrl } from "../pod";
import { PrimaryButton } from "./PrimaryButton";
import type { MissingReason, PickupChecklist as Checklist, PickupChecklistBox } from "../types";

const REASONS: { id: MissingReason; label: string }[] = [
  { id: "not_ready", label: "Not ready" },
  { id: "not_found", label: "Not found" },
  { id: "damaged", label: "Damaged" },
  { id: "wrong_item", label: "Wrong item" },
  { id: "other", label: "Other" },
];

type Props = {
  orderId: string;
  busy: boolean;
  /** Bumped by the parent after each scan so progress reloads. */
  refreshKey: number;
  onError: (message: string) => void;
  /** Called after a missing-box report so the parent refreshes scan progress. */
  onChanged: () => void;
};

function boxState(box: PickupChecklistBox): string {
  if (box.scanned) return "scanned";
  if (box.missing) return "reported missing";
  return "to scan";
}

/**
 * Pickup checklist per item: each box must be scanned or reported missing
 * (photo + reason) before pickup can be confirmed. Labels say "Item n · box
 * x of N" — the same words printed on the box label.
 */
export function PickupChecklist({ orderId, busy, refreshKey, onError, onChanged }: Props) {
  const [list, setList] = useState<Checklist | null>(null);
  const [openBox, setOpenBox] = useState<string | null>(null);
  const [reason, setReason] = useState<MissingReason | null>(null);
  const [photo, setPhoto] = useState<string | null>(null);
  const [action, setAction] = useState<string | null>(null);

  const load = useCallback(() => {
    void fetchPickupChecklist(orderId)
      .then(setList)
      .catch((err: unknown) => onError(err instanceof Error ? err.message : "checklist_failed"));
  }, [orderId, onError]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  if (!list || list.whole_vehicle || list.required === 0) return null;
  const locked = busy || Boolean(action);

  return (
    <View style={styles.wrap} testID="pickup-checklist">
      <Text style={styles.title}>
        Pickup checklist · {list.scanned + list.missing}/{list.required}
      </Text>
      {list.items.map((item) => (
        <View key={item.item_key ?? item.label} style={styles.item}>
          <Text style={item.complete ? styles.done : styles.body}>
            {item.label}
            {item.box_count > 1
              ? ` · ${item.scanned + item.missing} of ${item.box_count} boxes`
              : ""}
            {item.complete ? " ✓" : ""}
          </Text>
          {item.boxes.map((box) => (
            <View key={box.package_id}>
              <Text style={styles.meta}>
                {item.box_count > 1 ? `Box ${box.box_index ?? "?"} of ${item.box_count}` : "Box"} ·{" "}
                {box.tracking_suffix} · {boxState(box)}
              </Text>
              {!box.scanned && !box.missing ? (
                openBox === box.package_id ? (
                  <View style={styles.report}>
                    {REASONS.map((r) => (
                      <PrimaryButton
                        key={r.id}
                        tone={reason === r.id ? "danger" : "ghost"}
                        label={r.label}
                        disabled={locked}
                        onPress={() => setReason(r.id)}
                      />
                    ))}
                    <PrimaryButton
                      tone="ghost"
                      label={
                        action === "photo"
                          ? "Opening camera…"
                          : photo
                            ? "Retake photo"
                            : "Photo required"
                      }
                      disabled={locked}
                      onPress={() => {
                        setAction("photo");
                        void capturePodPhotoDataUrl()
                          .then(setPhoto)
                          .catch((err: unknown) =>
                            onError(err instanceof Error ? err.message : "photo_failed")
                          )
                          .finally(() => setAction(null));
                      }}
                    />
                    <PrimaryButton
                      tone="danger"
                      testID="submit-missing-box"
                      label={action === "report" ? "Reporting…" : "Report box missing"}
                      disabled={locked || !reason || !photo}
                      onPress={() => {
                        if (!reason || !photo) return;
                        setAction("report");
                        void reportPackageMissing(orderId, box.package_id, {
                          photo_url: photo,
                          reason,
                        })
                          .then((res) => {
                            setList(res.checklist);
                            setOpenBox(null);
                            setReason(null);
                            setPhoto(null);
                            onChanged();
                          })
                          .catch((err: unknown) =>
                            onError(err instanceof Error ? err.message : "report_missing_failed")
                          )
                          .finally(() => setAction(null));
                      }}
                    />
                  </View>
                ) : (
                  <PrimaryButton
                    tone="ghost"
                    label="Not here? Report missing"
                    disabled={locked}
                    onPress={() => {
                      setOpenBox(box.package_id);
                      setReason(null);
                      setPhoto(null);
                    }}
                  />
                )
              ) : null}
            </View>
          ))}
        </View>
      ))}
      <Text style={list.can_confirm ? styles.done : styles.meta} testID="pickup-can-confirm">
        {list.can_confirm
          ? "All boxes accounted for — you can confirm pickup"
          : "Scan every box, or report it missing, to confirm pickup"}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.muted,
    borderRadius: radius.lg,
    padding: spacing.sm,
  },
  title: {
    ...typography.body,
    fontWeight: "600",
    color: colors.primary,
  },
  item: {
    gap: spacing.xs,
  },
  report: {
    gap: spacing.xs,
  },
  body: {
    ...typography.body,
    color: colors.primary,
  },
  done: {
    ...typography.body,
    color: colors.secondary,
    fontWeight: "600",
  },
  meta: {
    ...typography.caption,
    color: colors.muted,
  },
});
