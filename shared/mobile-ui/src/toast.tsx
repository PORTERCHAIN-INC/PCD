"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { View } from "react-native";
import Animated, { FadeInUp, FadeOutUp } from "react-native-reanimated";
import { shadowForScheme, useTheme } from "@porterchain/mobile-theme";
import { Body } from "./typography";

export type ToastTone = "neutral" | "success" | "warning" | "danger";

type ToastItem = {
  id: string;
  message: string;
  tone: ToastTone;
};

type ToastContextValue = {
  show: (message: string, tone?: ToastTone) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const { theme } = useTheme();
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const show = useCallback((message: string, tone: ToastTone = "neutral") => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev, { id, message, tone }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3200);
  }, []);

  const value = useMemo(() => ({ show }), [show]);

  const toneBg: Record<ToastTone, string> = {
    neutral: theme.colors.surfaceElevated,
    success: theme.colors.successSoft,
    warning: theme.colors.warningSoft,
    danger: theme.colors.dangerSoft,
  };

  const toneText: Record<ToastTone, string> = {
    neutral: theme.colors.text,
    success: theme.colors.success,
    warning: theme.colors.warning,
    danger: theme.colors.danger,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <View
        pointerEvents="box-none"
        style={{
          position: "absolute",
          top: theme.spacing["3xl"],
          left: theme.spacing.lg,
          right: theme.spacing.lg,
          gap: theme.spacing.sm,
          zIndex: 9999,
        }}
      >
        {toasts.map((toast) => (
          <Animated.View
            key={toast.id}
            entering={FadeInUp.duration(theme.motion.duration.fast)}
            exiting={FadeOutUp.duration(theme.motion.duration.fast)}
            style={{
              paddingVertical: theme.spacing.md,
              paddingHorizontal: theme.spacing.lg,
              borderRadius: theme.radii.md,
              backgroundColor: toneBg[toast.tone],
              borderWidth: 1,
              borderColor: theme.colors.border,
              ...shadowForScheme("lg", theme.scheme),
            }}
          >
            <Body style={{ color: toneText[toast.tone], fontWeight: "500", textAlign: "center" }}>
              {toast.message}
            </Body>
          </Animated.View>
        ))}
      </View>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
