"use client";

import { FaGoogle } from "react-icons/fa6";
import { Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";
import {
  getGoogleBusinessProfileUrl,
  getGoogleBusinessReviewUrl,
  isGoogleBusinessProfileConfigured,
  isGoogleBusinessReviewConfigured,
} from "@/lib/google-business";

type Variant = "footer" | "contact" | "inline";

interface GoogleBusinessProfileLinkProps {
  variant?: Variant;
  className?: string;
  /** Show “Write a review on Google” when review URL is available. */
  showReview?: boolean;
  label?: string;
  reviewLabel?: string;
}

const variantStyles: Record<Variant, { wrap: string; link: string; icon: string }> = {
  footer: {
    wrap: "flex flex-wrap gap-3",
    link: "inline-flex items-center gap-2 text-white/50 type-small hover:text-white transition-colors",
    icon: "w-4 h-4",
  },
  contact: {
    wrap: "flex flex-col sm:flex-row gap-3",
    link: "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-full border border-secondary/25 bg-secondary/5 text-secondary font-semibold text-sm hover:bg-secondary hover:text-white transition-colors",
    icon: "w-4 h-4",
  },
  inline: {
    wrap: "inline-flex flex-wrap gap-2",
    link: "inline-flex items-center gap-1.5 text-secondary font-semibold text-sm hover:underline",
    icon: "w-4 h-4",
  },
};

export default function GoogleBusinessProfileLink({
  variant = "inline",
  className,
  showReview = true,
  label = "Find us on Google",
  reviewLabel = "Review us on Google",
}: GoogleBusinessProfileLinkProps) {
  if (!isGoogleBusinessProfileConfigured()) {
    return null;
  }

  const styles = variantStyles[variant];
  const profileUrl = getGoogleBusinessProfileUrl();
  const reviewUrl = getGoogleBusinessReviewUrl();

  return (
    <div className={cn(styles.wrap, className)}>
      <a
        href={profileUrl}
        target="_blank"
        rel="noopener noreferrer"
        className={styles.link}
        onClick={() =>
          track(ANALYTICS_EVENTS.GBP_PROFILE_CLICK, {
            source_section: variant,
            link_type: "profile",
          })
        }
      >
        <FaGoogle className={styles.icon} aria-hidden />
        {label}
      </a>
      {showReview && isGoogleBusinessReviewConfigured() && (
        <a
          href={reviewUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={styles.link}
          onClick={() =>
            track(ANALYTICS_EVENTS.GBP_REVIEW_CLICK, {
              source_section: variant,
              link_type: "review",
            })
          }
        >
          <Star className={styles.icon} aria-hidden />
          {reviewLabel}
        </a>
      )}
    </div>
  );
}
