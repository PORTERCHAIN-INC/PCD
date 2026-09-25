import { cn } from "@/lib/utils";

type Props = {
  label: string;
  tone?: "neutral" | "success" | "warning" | "info";
  className?: string;
};

const tones = {
  neutral: "bg-primary/5 text-primary",
  success: "bg-secondary/10 text-secondary",
  warning: "bg-amber-50 text-amber-800",
  info: "bg-secondary/10 text-secondary",
} as const;

export default function HubStatusChip({ label, tone = "info", className }: Props) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold",
        tones[tone],
        className
      )}
    >
      {label}
    </span>
  );
}
