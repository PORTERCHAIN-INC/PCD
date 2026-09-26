import { redirect } from "next/navigation";

/** Permanent alias — merged into /system?tab=tests. Do not add a separate page. */
export default function SystemTestsRedirectPage() {
  redirect("/system?tab=tests");
}
