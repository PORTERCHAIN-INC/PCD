import { useEffect } from "react";
import { AccessibilityInfo } from "react-native";

export function useScreenReaderEnabled() {
  useEffect(() => {
    void AccessibilityInfo.isScreenReaderEnabled();
  }, []);
}

export function a11yProps(label: string, hint?: string) {
  return {
    accessible: true,
    accessibilityRole: "button" as const,
    accessibilityLabel: label,
    ...(hint ? { accessibilityHint: hint } : {}),
  };
}
