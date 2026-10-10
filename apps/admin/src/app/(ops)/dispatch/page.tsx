import { redirect } from "next/navigation";

export default function DispatchIndex() {
  redirect("/dispatch/today");
}
