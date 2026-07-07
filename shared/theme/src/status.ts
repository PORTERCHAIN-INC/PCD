import type { ThemeColors } from "./colors";

export type StatusTone =
  | "neutral"
  | "info"
  | "success"
  | "warning"
  | "danger"
  | "active"
  | "pending"
  | "completed"
  | "cancelled";

export function statusTone(colors: ThemeColors, tone: StatusTone) {
  const map: Record<StatusTone, { bg: string; text: string; border: string }> = {
    neutral: { bg: colors.surfaceMuted, text: colors.textSecondary, border: colors.border },
    info: { bg: colors.infoSoft, text: colors.info, border: "transparent" },
    success: { bg: colors.successSoft, text: colors.success, border: "transparent" },
    warning: { bg: colors.warningSoft, text: colors.warning, border: "transparent" },
    danger: { bg: colors.dangerSoft, text: colors.danger, border: "transparent" },
    active: { bg: colors.secondaryMuted, text: colors.secondary, border: "transparent" },
    pending: { bg: colors.warningSoft, text: colors.warning, border: "transparent" },
    completed: { bg: colors.successSoft, text: colors.success, border: "transparent" },
    cancelled: { bg: colors.dangerSoft, text: colors.danger, border: "transparent" },
  };
  return map[tone];
}
