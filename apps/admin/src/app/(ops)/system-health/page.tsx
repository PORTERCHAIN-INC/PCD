import { redirect } from "next/navigation";

/** Merged into /system (Health tab). */
export default function SystemHealthRedirectPage() {
  redirect("/system");
}
