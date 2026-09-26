import { redirect } from "next/navigation";

/** Permanent alias for legacy /admin/system-health → /system. */
export default function LegacyAdminSystemHealthPage() {
  redirect("/system");
}
