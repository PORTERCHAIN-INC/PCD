import { cn } from "@/lib/utils";

/**
 * One heading pattern for every marketing section (type scale: eyebrow 14/0.14em caps,
 * H2 30→40 px, lead 18 px) so home, calculator and /delivery pages share the same rhythm.
 */
export default function SectionHeader({
  id,
  eyebrow,
  title,
  lead,
  tone = "light",
  align = "left",
  className,
  as: Heading = "h2",
}: {
  id?: string;
  eyebrow?: string;
  title: string;
  lead?: string;
  tone?: "light" | "dark";
  align?: "left" | "center";
  className?: string;
  as?: "h1" | "h2";
}) {
  const dark = tone === "dark";
  return (
    <div className={cn("max-w-2xl", align === "center" && "mx-auto text-center", className)}>
      {eyebrow ? (
        <p
          className={cn(
            "text-sm font-semibold uppercase tracking-[0.14em]",
            dark ? "text-[#93c5fd]" : "text-secondary"
          )}
        >
          {eyebrow}
        </p>
      ) : null}
      <Heading
        id={id}
        className={cn(
          "text-balance text-3xl font-semibold tracking-tight sm:text-4xl",
          eyebrow && "mt-2",
          dark ? "text-white" : "text-primary"
        )}
      >
        {title}
      </Heading>
      {lead ? (
        <p className={cn("mt-3 text-lg leading-relaxed", dark ? "text-white/75" : "text-muted")}>
          {lead}
        </p>
      ) : null}
    </div>
  );
}
