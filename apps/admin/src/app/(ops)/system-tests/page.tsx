import { redirect } from "next/navigation";

/** Merged into /system?tab=tests. */
export default function SystemTestsRedirectPage() {
  redirect("/system?tab=tests");
}
