import { Text, View, StyleSheet } from "react-native";
import LottieView from "lottie-react-native";
import { colors, radius, typography } from "@porterchain/mobile-theme";
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

export function EmptyState({
  animation,
  title,
  body,
}: {
  animation?: MotionName;
  title: string;
  body: string;
}) {
  return (
    <View style={styles.card}>
      {animation ? <Motion name={animation} /> : null}
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.body}>{body}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    alignItems: "center",
    paddingHorizontal: 20,
    paddingBottom: 20,
    paddingTop: 4,
    gap: 4,
  },
  title: { ...typography.body, color: colors.primary, fontWeight: "700", textAlign: "center" },
  body: { ...typography.caption, color: colors.muted, textAlign: "center" },
});
