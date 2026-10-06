import { redirect } from "next/navigation";

export default function VehicleRedirectPage() {
  redirect("/profile#vehicle");
}
