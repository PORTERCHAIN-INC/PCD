"use client";

import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";

const NavigationClient = dynamic(() => import("@/components/navigation/NavigationClient"), {
  loading: () => (
    <div className="p-4">
      <PageSkeleton rows={3} />
    </div>
  ),
});

export default function NavigationPage() {
  return <NavigationClient />;
}
