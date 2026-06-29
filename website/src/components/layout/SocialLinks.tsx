"use client";

import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { SOCIAL_ICONS, SOCIAL_LINKS, type SocialLinkItem } from "@/data/social-links";

type SocialLinksVariant = "footer" | "contact";

interface SocialLinksProps {
  variant?: SocialLinksVariant;
  className?: string;
  links?: SocialLinkItem[];
}

const variantStyles: Record<SocialLinksVariant, string> = {
  footer:
    "touch-target w-11 h-11 rounded-lg bg-white/10 flex items-center justify-center hover:bg-secondary transition-colors text-white/90 hover:text-white",
  contact:
    "w-11 h-11 rounded-xl bg-gray-bg border border-primary/[0.06] flex items-center justify-center text-primary/70 hover:bg-secondary hover:text-white hover:border-secondary transition-all hover:scale-105",
};

export default function SocialLinks({
  variant = "footer",
  className,
  links = SOCIAL_LINKS,
}: SocialLinksProps) {
  const iconClass = variant === "footer" ? "w-[18px] h-[18px]" : "w-5 h-5";

  return (
    <div className={cn("flex flex-wrap gap-3", className)}>
      {links.map((link) => {
        const Icon = SOCIAL_ICONS[link.platform];
        const classNames = variantStyles[variant];

        if (link.internal) {
          return (
            <Link
              key={link.platform}
              href={link.href}
              aria-label={link.label}
              className={classNames}
            >
              <Icon className={iconClass} aria-hidden />
            </Link>
          );
        }

        return (
          <a
            key={link.platform}
            href={link.href}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={link.label}
            className={classNames}
          >
            <Icon className={iconClass} aria-hidden />
          </a>
        );
      })}
    </div>
  );
}
