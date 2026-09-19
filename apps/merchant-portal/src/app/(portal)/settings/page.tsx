import { Suspense } from "react";
import SettingsClient from "@/components/settings/SettingsClient";

export default function SettingsPage() {
  return (
    <Suspense fallback={<p className="text-muted">Loading…</p>}>
      <SettingsClient />
    </Suspense>
  );
}
