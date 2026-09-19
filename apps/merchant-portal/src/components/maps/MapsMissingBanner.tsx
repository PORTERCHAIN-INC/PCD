"use client";

import { isGoogleMapsConfigured } from "@/lib/env";

/** Same banner Track uses when Places/Maps has no Google key (BS). */
export default function MapsMissingBanner() {
  if (isGoogleMapsConfigured()) return null;
  return (
    <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900">
      The map needs a Google Maps key in this environment.
    </p>
  );
}
