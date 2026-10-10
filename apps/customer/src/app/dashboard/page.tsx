import { redirect } from "next/navigation";

/** Home + Track + Invoices merged into Orders. */
export default function DashboardPage() {
  redirect("/orders");
}
