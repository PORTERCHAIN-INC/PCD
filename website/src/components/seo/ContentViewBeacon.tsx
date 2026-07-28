"use client";

import { useEffect } from "react";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";

type Props = {
  kind: "guide" | "comparison" | "case_study" | "industry" | "location" | "vehicle";
  slug: string;
  source?: string;
};

const EVENT_BY_KIND = {
  guide: ANALYTICS_EVENTS.GUIDE_VIEWED,
  comparison: ANALYTICS_EVENTS.COMPARISON_VIEWED,
  case_study: ANALYTICS_EVENTS.CASE_STUDY_VIEWED,
  industry: ANALYTICS_EVENTS.INDUSTRY_PAGE_VIEW,
  location: ANALYTICS_EVENTS.LOCATION_PAGE_VIEW,
  vehicle: ANALYTICS_EVENTS.VEHICLE_PAGE_VIEW,
} as const;

/** Fire once on mount for content page view events. */
export default function ContentViewBeacon({ kind, slug, source }: Props) {
  useEffect(() => {
    track(EVENT_BY_KIND[kind], {
      slug,
      source_section: source ?? kind,
    });
  }, [kind, slug, source]);

  return null;
}
