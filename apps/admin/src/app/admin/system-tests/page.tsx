import { redirect } from "next/navigation";

export default function LegacyAdminSystemTestsPage() {
  redirect("/system?tab=tests");
}
