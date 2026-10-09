import { getTranslations } from "next-intl/server";
import { Camera, MapPinned, ShieldCheck } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

/**
 * Factual badge row: insured (COI on request — the claim already published on /trust/insurance),
 * live tracking and photo proof of delivery (both shipped product features). No ratings, no counts.
 */
const BADGES = [
  { id: "insured", Icon: ShieldCheck, href: "/trust/insurance" },
  { id: "tracked", Icon: MapPinned, href: "/track" },
  { id: "pod", Icon: Camera, href: null },
] as const;

export default async function TrustBadges({
  locale,
  tone = "light",
  className,
}: {
  locale: string;
  tone?: "light" | "dark";
  className?: string;
}) {
  const t = await getTranslations({ locale, namespace: "marketing.trustBadges" });
  const dark = tone === "dark";
  const item = cn(
    "inline-flex min-h-[2rem] items-center gap-2 rounded-full text-sm font-medium",
    dark ? "text-white/85" : "text-primary/85"
  );
  const icon = cn("h-4 w-4 shrink-0", dark ? "text-[#86efac]" : "text-emerald-700");
  return (
    <ul
      aria-label={t("ariaLabel")}
      className={cn("flex flex-wrap items-center gap-x-5 gap-y-2", className)}
    >
      {BADGES.map(({ id, Icon, href }) => (
        <li key={id}>
          {href ? (
            <Link
              href={href}
              className={cn(
                item,
                "underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2",
                dark ? "focus-visible:ring-white" : "focus-visible:ring-secondary"
              )}
            >
              <Icon className={icon} aria-hidden />
              {t(id)}
            </Link>
          ) : (
            <span className={item}>
              <Icon className={icon} aria-hidden />
              {t(id)}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}
