"use client";

import { useEffect } from "react";
import { captureAttribution } from "@/lib/seo/attribution";

/** Capture UTM and landing context once per session for lead attribution. */
export default function AttributionCapture() {
  useEffect(() => {
    captureAttribution();
  }, []);
  return null;
}
