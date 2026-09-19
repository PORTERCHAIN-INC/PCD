import { formatState, STATE_STYLES } from "@/lib/orders";
import { cn } from "@/lib/utils";

export function OrderStateBadge({ state, displayState }: { state: string; displayState?: string }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
        STATE_STYLES[state] ?? "bg-gray-100 text-gray-700"
      )}
    >
      {displayState || formatState(state)}
    </span>
  );
}
