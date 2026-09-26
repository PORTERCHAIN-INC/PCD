import { redirect } from "next/navigation";

/** Permanent alias — merged into /system (Health tab). Do not add a separate page. */
export default function SystemHealthRedirectPage() {
  redirect("/system");
}
