import { useCallback, useEffect, useRef, useState } from "react";
import { PanResponder, View, StyleSheet, type LayoutChangeEvent } from "react-native";
import { signatureReady, strokesToPngDataUrl } from "@porterchain/driver-flows";
import { color, radius, space } from "./theme";

type Point = { x: number; y: number };
type Stroke = Point[];

type Props = {
  disabled?: boolean;
  onChange: (signatureData: string) => void;
};

/** PNG (not SVG): the API stores signatures as PNG only. Scaled to ≤ 360 px wide to stay well under 300 KB. */
function strokesToPng(strokes: Stroke[], width: number, height: number): string {
  const k = Math.min(1, 360 / Math.max(1, width));
  return strokesToPngDataUrl(
    strokes.map((st) => st.map((p) => ({ x: p.x * k, y: p.y * k }))),
    width * k,
    height * k
  );
}

export function SignaturePad({ disabled, onChange }: Props) {
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const sizeRef = useRef({ width: 300, height: 140 });
  const strokesRef = useRef<Stroke[]>([]);
  const currentRef = useRef<Stroke>([]);
  const onChangeRef = useRef(onChange);
  const disabledRef = useRef(disabled);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);
  useEffect(() => {
    disabledRef.current = disabled;
  }, [disabled]);

  const publish = useCallback((next: Stroke[]) => {
    strokesRef.current = next;
    setStrokes(next);
    if (next.length === 0 || !signatureReady(next)) {
      onChangeRef.current("");
      return;
    }
    const { width, height } = sizeRef.current;
    onChangeRef.current(strokesToPng(next, width, height));
  }, []);

  const responder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => !disabledRef.current,
      onMoveShouldSetPanResponder: () => !disabledRef.current,
      onPanResponderGrant: (evt) => {
        currentRef.current = [{ x: evt.nativeEvent.locationX, y: evt.nativeEvent.locationY }];
      },
      onPanResponderMove: (evt) => {
        currentRef.current = [
          ...currentRef.current,
          { x: evt.nativeEvent.locationX, y: evt.nativeEvent.locationY },
        ];
        // Live preview: committed strokes + in-progress stroke
        const live = [...strokesRef.current, currentRef.current];
        setStrokes(live);
      },
      onPanResponderRelease: () => {
        if (currentRef.current.length) {
          publish([...strokesRef.current, currentRef.current]);
        }
        currentRef.current = [];
      },
    })
  ).current;

  return (
    <View
      testID="signature-pad"
      accessibilityLabel="Signature box. Receiver signs here with a finger."
      style={[styles.pad, disabled ? styles.disabled : null]}
      onLayout={(e: LayoutChangeEvent) => {
        const { width, height } = e.nativeEvent.layout;
        sizeRef.current = { width, height };
      }}
      {...responder.panHandlers}
    >
      {strokes.map((stroke, si) =>
        stroke.slice(1).map((point, pi) => {
          const prev = stroke[pi];
          const dx = point.x - prev.x;
          const dy = point.y - prev.y;
          const len = Math.sqrt(dx * dx + dy * dy) || 1;
          const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
          return (
            <View
              key={`${si}-${pi}`}
              pointerEvents="none"
              style={[
                styles.segment,
                {
                  left: prev.x,
                  top: prev.y,
                  width: len,
                  transform: [{ rotate: `${angle}deg` }],
                },
              ]}
            />
          );
        })
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  pad: {
    minHeight: 220,
    borderWidth: 2,
    borderColor: color.ink,
    borderStyle: "dashed",
    borderRadius: radius.lg,
    backgroundColor: color.surface,
    overflow: "hidden",
    marginBottom: space.xs,
  },
  disabled: { opacity: 0.5 },
  segment: {
    position: "absolute",
    height: 3,
    backgroundColor: color.ink,
    borderRadius: 2,
    transformOrigin: "left center",
  },
});
