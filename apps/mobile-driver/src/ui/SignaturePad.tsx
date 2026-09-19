import { useCallback, useEffect, useRef, useState } from "react";
import { PanResponder, View, StyleSheet, type LayoutChangeEvent } from "react-native";
import { colors, radius, spacing } from "@porterchain/mobile-theme";

type Point = { x: number; y: number };
type Stroke = Point[];

type Props = {
  disabled?: boolean;
  onChange: (signatureData: string) => void;
};

function encodeSvgDataUrl(svg: string): string {
  if (typeof globalThis.btoa === "function") {
    return `data:image/svg+xml;base64,${globalThis.btoa(svg)}`;
  }
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function strokesToSvg(strokes: Stroke[], width: number, height: number): string {
  const paths = strokes
    .filter((s) => s.length > 0)
    .map((stroke) => {
      const [first, ...rest] = stroke;
      const d = [`M ${first.x.toFixed(1)} ${first.y.toFixed(1)}`]
        .concat(rest.map((p) => `L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`))
        .join(" ");
      return `<path d="${d}" fill="none" stroke="#111827" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>`;
    })
    .join("");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${Math.round(width)}" height="${Math.round(height)}" viewBox="0 0 ${Math.round(width)} ${Math.round(height)}">${paths}</svg>`;
  return encodeSvgDataUrl(svg);
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
    if (next.length === 0) {
      onChangeRef.current("");
      return;
    }
    const { width, height } = sizeRef.current;
    onChangeRef.current(strokesToSvg(next, width, height));
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
    minHeight: 140,
    borderWidth: 1,
    borderColor: colors.muted,
    borderRadius: radius.lg,
    backgroundColor: "#fafafa",
    overflow: "hidden",
    marginBottom: spacing.xs,
  },
  disabled: { opacity: 0.5 },
  segment: {
    position: "absolute",
    height: 2.5,
    backgroundColor: colors.primary,
    borderRadius: 2,
    transformOrigin: "left center",
  },
});
