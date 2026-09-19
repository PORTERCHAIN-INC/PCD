import { redirect } from "next/navigation";

export default function BulkPage() {
  redirect("/routes?tab=csv");
}
