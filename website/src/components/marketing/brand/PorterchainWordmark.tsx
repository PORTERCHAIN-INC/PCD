import { cn } from "@/lib/utils";

type PorterchainWordmarkProps = {
  /** Light page backgrounds use the navy knot; dark bars use the white knot. */
  tone?: "light" | "dark";
  size?: "sm" | "md" | "lg";
  className?: string;
};

const sizeClasses = {
  sm: "text-sm",
  md: "text-[0.95rem] md:text-base",
  lg: "text-lg md:text-xl",
} as const;

const markSrc = {
  light: "/brand/porterchain-mark.png",
  dark: "/brand/porterchain-mark-white.png",
} as const;

/** Knot mark plus lowercase wordmark. The mark scales with the type so it stays inside the nav and footer. */
export default function PorterchainWordmark({
  tone = "light",
  size = "md",
  className,
}: PorterchainWordmarkProps) {
  const textTone = tone === "light" ? "text-primary" : "text-white";

  return (
    <span
      className={cn(
        "inline-flex max-w-full items-center gap-[0.4em] leading-none whitespace-nowrap select-none",
        sizeClasses[size],
        textTone,
        className
      )}
      aria-hidden
    >
      <img
        src={markSrc[tone]}
        alt=""
        className="block shrink-0"
        style={{ height: "1.55em", width: "auto" }}
      />
      <span className="font-semibold tracking-[0.01em]">porterchain</span>
    </span>
  );
}
