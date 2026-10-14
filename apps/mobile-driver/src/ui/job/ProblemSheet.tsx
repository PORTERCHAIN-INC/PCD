/** "Can't complete this stop": pick a reason (photo when required), report to dispatch. */
import { useState } from "react";
import { Pressable, StyleSheet } from "react-native";
import { capturePodPhotoDataUrl } from "../../pod";
import { STOP_EXCEPTION_TYPES, stopExceptionById } from "../../stopExceptions";
import { Body, Button, Strong } from "../kit";
import { Sheet } from "../Sheet";
import { color, radius, space, target } from "../theme";

export function ProblemSheet({
  visible,
  busy,
  onClose,
  onReport,
  onError,
}: {
  visible: boolean;
  busy: boolean;
  onClose: () => void;
  onReport: (reason: string, photoUrl?: string) => void;
  onError: (message: string) => void;
}) {
  const [code, setCode] = useState<string | null>(null);
  const [photo, setPhoto] = useState<string | null>(null);
  const needsPhoto = Boolean(code && stopExceptionById(code)?.photoRequired);

  return (
    <Sheet
      visible={visible}
      title="Can't complete this stop"
      onClose={onClose}
      testID="sheet-problem"
      footer={
        <>
          {needsPhoto ? (
            <Button
              label={photo ? "Retake photo" : "Take photo (required)"}
              onPress={() =>
                void capturePodPhotoDataUrl()
                  .then(setPhoto)
                  .catch((e: unknown) => onError(e instanceof Error ? e.message : "photo_failed"))
              }
            />
          ) : null}
          <Button
            tone="danger"
            label="Report to dispatch"
            busy={busy}
            disabled={!code || (needsPhoto && !photo)}
            onPress={() => code && onReport(code, photo ?? undefined)}
          />
        </>
      }
    >
      <Body>What happened?</Body>
      {STOP_EXCEPTION_TYPES.map((item) => {
        const on = code === item.id;
        return (
          <Pressable
            key={item.id}
            accessibilityRole="radio"
            accessibilityState={{ selected: on }}
            onPress={() => {
              setCode(item.id);
              setPhoto(null);
            }}
            style={[styles.choice, on && styles.on]}
          >
            <Strong style={on ? styles.onText : undefined}>{item.label}</Strong>
          </Pressable>
        );
      })}
    </Sheet>
  );
}

const styles = StyleSheet.create({
  choice: {
    minHeight: target.min,
    borderRadius: radius.md,
    borderWidth: 2,
    borderColor: color.ink,
    backgroundColor: color.surface,
    paddingHorizontal: space.lg,
    justifyContent: "center",
  },
  on: { backgroundColor: color.danger, borderColor: color.danger },
  onText: { color: color.onPrimary },
});
