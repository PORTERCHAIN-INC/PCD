import { cn } from "@/lib/utils";

type PorterchainWordmarkProps = {
  /** Light page backgrounds use dark text; dark bars use light text. */
  tone?: "light" | "dark";
  size?: "sm" | "md" | "lg";
  className?: string;
};

const sizeClasses = {
  sm: "text-sm",
  md: "text-base md:text-[1.1rem]",
  lg: "text-lg md:text-[1.25rem]",
} as const;

/** Font-only wordmark — capitalized Porterchain, tight tracking. */
export default function PorterchainWordmark({
  tone = "light",
  size = "md",
  className,
}: PorterchainWordmarkProps) {
  const textTone = tone === "light" ? "text-primary" : "text-white";

  return (
    <span
      className={cn(
        "font-semibold tracking-[0.04em] leading-none select-none",
        sizeClasses[size],
        textTone,
        className
      )}
      aria-hidden
    >
      Porterchain
    </span>
  );
}
