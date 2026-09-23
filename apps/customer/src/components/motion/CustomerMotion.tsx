"use client";

import Lottie from "lottie-react";
import shipment from "@porterchain/customer-motion/shipment.json";
import route from "@porterchain/customer-motion/route.json";
import inbox from "@porterchain/customer-motion/inbox.json";

const SOURCES = {
  shipment,
  route,
  inbox,
} as const;

export type CustomerMotionName = keyof typeof SOURCES;

export default function CustomerMotion({
  name,
  size = 160,
}: {
  name: CustomerMotionName;
  size?: number;
}) {
  return (
    <Lottie
      animationData={SOURCES[name]}
      loop
      style={{ width: size, height: size, marginInline: "auto" }}
    />
  );
}
