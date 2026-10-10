import { cn } from "@porterchain/ui/utils";

export const BAND_LABEL = { healthy: "Healthy", watch: "Watch", at_risk: "At risk" } as const;

export function ScoreRing({ score, size = "md" }: { score: number; size?: "sm" | "md" }) {
  const color = score >= 70 ? "#15803d" : score >= 40 ? "#b45309" : "#b91c1c";
  const outer = size === "sm" ? "h-9 w-9" : "h-16 w-16";
  const inner = size === "sm" ? "h-7 w-7 text-xs" : "h-12 w-12 text-base";
  return (
    <div
      className={cn("relative flex shrink-0 items-center justify-center rounded-full", outer)}
      style={{ background: `conic-gradient(${color} ${score * 3.6}deg, #e2e8f0 0deg)` }}
      aria-label={`Health ${score} of 100`}
      role="img"
    >
      <div
        className={cn(
          "flex items-center justify-center rounded-full bg-white font-bold tabular-nums text-primary",
          inner
        )}
      >
        {score}
      </div>
    </div>
  );
}
