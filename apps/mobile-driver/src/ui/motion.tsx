/** Motion primitives (Reanimated): press-scale, entrance fade/rise, skeleton shimmer, live dot. */
import { useEffect, type ReactNode } from "react";
import { Pressable, type PressableProps, type StyleProp, type ViewStyle, View } from "react-native";
import Animated, {
  Easing,
  FadeInDown,
  ReduceMotion,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withSequence,
  withSpring,
  withTiming,
} from "react-native-reanimated";
import { color, motion, radius } from "./theme";

const APressable = Animated.createAnimatedComponent(Pressable);

/** Pressable that physically gives a little under the thumb. */
export function PressScale({
  style,
  children,
  ...rest
}: PressableProps & { style?: StyleProp<ViewStyle>; children?: ReactNode }) {
  const scale = useSharedValue(1);
  const anim = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  return (
    <APressable
      {...rest}
      onPressIn={(e) => {
        scale.value = withSpring(motion.pressScale, { damping: 20, stiffness: 400 });
        rest.onPressIn?.(e);
      }}
      onPressOut={(e) => {
        scale.value = withSpring(1, { damping: 14, stiffness: 300 });
        rest.onPressOut?.(e);
      }}
      style={[style, anim]}
    >
      {children}
    </APressable>
  );
}

/** Content rises in once on mount (skipped when the OS asks for reduced motion). */
export function Rise({
  children,
  index = 0,
  style,
}: {
  children: ReactNode;
  index?: number;
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <Animated.View
      entering={FadeInDown.duration(motion.base)
        .delay(index * 50)
        .reduceMotion(ReduceMotion.System)}
      style={style}
    >
      {children}
    </Animated.View>
  );
}

/** Loading placeholder with a soft pulse. */
export function Skeleton({
  height = 18,
  width = "100%",
  style,
}: {
  height?: number;
  width?: number | `${number}%`;
  style?: StyleProp<ViewStyle>;
}) {
  const reduced = useReducedMotion();
  const o = useSharedValue(0.55);
  useEffect(() => {
    if (reduced) return;
    o.value = withRepeat(
      withSequence(
        withTiming(1, { duration: 700, easing: Easing.inOut(Easing.quad) }),
        withTiming(0.55, { duration: 700, easing: Easing.inOut(Easing.quad) })
      ),
      -1
    );
  }, [o, reduced]);
  const anim = useAnimatedStyle(() => ({ opacity: o.value }));
  return (
    <Animated.View
      accessibilityElementsHidden
      importantForAccessibility="no"
      style={[
        { height, width, borderRadius: radius.sm, backgroundColor: color.skeleton },
        anim,
        style,
      ]}
    />
  );
}

/** Breathing dot for "live" state (on duty, GPS sharing). */
export function LiveDot({ on, size = 10 }: { on: boolean; size?: number }) {
  const reduced = useReducedMotion();
  const s = useSharedValue(1);
  useEffect(() => {
    if (!on || reduced) {
      s.value = 1;
      return;
    }
    s.value = withRepeat(
      withSequence(withTiming(1.8, { duration: 900 }), withTiming(1, { duration: 0 })),
      -1
    );
  }, [on, reduced, s]);
  const halo = useAnimatedStyle(() => ({
    transform: [{ scale: s.value }],
    opacity: 2 - s.value - 0.2,
  }));
  const c = on ? color.primary : color.inkFaint;
  return (
    <View
      style={{ width: size * 2, height: size * 2, alignItems: "center", justifyContent: "center" }}
    >
      {on ? (
        <Animated.View
          style={[
            {
              position: "absolute",
              width: size,
              height: size,
              borderRadius: size,
              backgroundColor: c,
            },
            halo,
          ]}
        />
      ) : null}
      <View style={{ width: size, height: size, borderRadius: size, backgroundColor: c }} />
    </View>
  );
}
