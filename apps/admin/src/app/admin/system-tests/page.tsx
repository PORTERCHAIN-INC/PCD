import { redirect } from "next/navigation";

/** Permanent alias for legacy /admin/system-tests → /system?tab=tests. */
export default function LegacyAdminSystemTestsPage() {
  redirect("/system?tab=tests");
}
