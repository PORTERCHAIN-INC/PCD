"use client";

import { Suspense } from "react";
import { Spinner } from "@/components/crm/primitives";
import SettingsCenter from "@/components/settings/SettingsCenter";

export default function SettingsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-20">
          <Spinner label="Loading settings…" />
        </div>
      }
    >
      <SettingsCenter />
    </Suspense>
  );
}
