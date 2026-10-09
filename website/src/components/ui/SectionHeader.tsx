import { cn } from "@/lib/utils";

interface SectionHeaderProps {
  label?: string;
  title: string;
  subtitle?: string;
  align?: "left" | "center";
  dark?: boolean;
  className?: string;
}

export default function SectionHeader({
  label,
  title,
  subtitle,
  align = "center",
  dark = false,
  className,
}: SectionHeaderProps) {
  return (
    <div
      className={cn(
        "mb-6 sm:mb-8 md:mb-9",
        align === "center" && "text-center mx-auto max-w-3xl",
        className
      )}
    >
      {label && (
        <span
          className={cn(
            "inline-block type-caption font-bold mb-2",
            // On navy sections the blue label fails AA (3.0:1); use the light accent there.
            dark ? "text-[#93c5fd]" : "text-secondary [.bg-primary_&]:text-[#93c5fd]"
          )}
        >
          {label}
        </span>
      )}
      <h2 className={cn("type-h2 text-balance", dark ? "text-white" : "text-primary")}>{title}</h2>
      {subtitle && (
        <p
          className={cn(
            "mt-3 type-lead max-w-2xl",
            align === "center" && "mx-auto",
            dark ? "text-white/70" : "text-muted"
          )}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
}
