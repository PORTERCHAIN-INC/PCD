"use client";

import dynamic from "next/dynamic";

const DriverProfileClient = dynamic(() => import("@/components/profile/DriverProfileClient"), {
  loading: () => (
    <div className="animate-pulse space-y-4 p-4">
      <div className="h-10 w-48 rounded-xl bg-white" />
      <div className="h-40 rounded-2xl bg-white" />
    </div>
  ),
});

export default function ProfilePage() {
  return <DriverProfileClient />;
}
