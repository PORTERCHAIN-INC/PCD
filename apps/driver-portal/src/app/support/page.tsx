"use client";

import dynamic from "next/dynamic";

const DriverSupportClient = dynamic(() => import("@/components/support/DriverSupportClient"), {
  loading: () => (
    <div className="animate-pulse space-y-4 p-4">
      <div className="h-10 w-48 rounded-xl bg-white" />
      <div className="h-32 rounded-2xl bg-white" />
    </div>
  ),
});

export default function SupportPage() {
  return <DriverSupportClient />;
}
