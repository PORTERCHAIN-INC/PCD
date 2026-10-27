import { Text, View, StyleSheet } from "react-native";
import LottieView from "lottie-react-native";
import { radius, typography } from "@porterchain/mobile-theme";
import { useThemed, type Palette } from "../theme";
import shipment from "@porterchain/customer-motion/shipment.json";
import route from "@porterchain/customer-motion/route.json";
import inbox from "@porterchain/customer-motion/inbox.json";

const SOURCES = {
  shipment,
  route,
  inbox,
} as const;

export type MotionName = keyof typeof SOURCES;

export function Motion({ name, size = 148 }: { name: MotionName; size?: number }) {
  return (
    <LottieView
      source={SOURCES[name]}
      autoPlay
      loop
      style={{ width: size, height: size, alignSelf: "center" }}
    />
  );
}
