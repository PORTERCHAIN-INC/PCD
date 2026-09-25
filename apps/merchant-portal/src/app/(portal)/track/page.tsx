"use client";

import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";

const TrackPageClient = dynamic(() => import("@/components/tracking/TrackPageClient"), {
  loading: () => <PageSkeleton rows={4} />,
});

export default function TrackPage() {
  return <TrackPageClient />;
}
