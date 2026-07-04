"use client";

import { type ReactNode } from "react";
import Animated, {
  FadeIn,
  FadeInDown,
  FadeInUp,
  FadeOut,
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from "react-native-reanimated";
import { Pressable, type PressableProps } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";

export { FadeIn, FadeInDown, FadeInUp, FadeOut };

export function AnimatedView({
  children,
  entering,
  exiting,
  style,
}: {
  children: ReactNode;
  entering?: typeof FadeIn;
  exiting?: typeof FadeOut;
  style?: object;
}) {
  return (
    <Animated.View entering={entering} exiting={exiting} style={style}>
      {children}
    </Animated.View>
  );
}

export function PressableScale({
  children,
  scale = 0.97,
  style,
  ...props
}: PressableProps & { scale?: number; children: ReactNode }) {
  const { theme } = useTheme();
  const pressed = useSharedValue(1);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: pressed.value }],
  }));

  return (
    <Pressable
      onPressIn={() => {
        pressed.value = withSpring(scale, theme.motion.spring);
      }}
      onPressOut={() => {
        pressed.value = withSpring(1, theme.motion.spring);
      }}
      style={style}
      {...props}
    >
      <Animated.View style={animatedStyle}>{children}</Animated.View>
    </Pressable>
  );
}
