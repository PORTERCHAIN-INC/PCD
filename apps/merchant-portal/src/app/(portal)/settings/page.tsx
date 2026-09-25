import { Suspense } from "react";
import SettingsClient from "@/components/settings/SettingsClient";

/** Maps JS loads only inside Profile/Locations tabs — not the whole settings shell. */
export default function SettingsPage() {
  return (
    <Suspense fallback={<p className="text-muted">Loading…</p>}>
      <SettingsClient />
    </Suspense>
  );
}
