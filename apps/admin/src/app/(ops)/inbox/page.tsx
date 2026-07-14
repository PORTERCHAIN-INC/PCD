import { redirect } from "next/navigation";

/** Legacy route — Notification Center lives at /notifications. */
export default function InboxRedirectPage() {
  redirect("/notifications?tab=inbox");
}
