import { redirect } from "next/navigation";

/** Drivers moved into Dispatch → Fleet. Driver detail stays at /drivers/[id]. */
export default function DriversRedirect() {
  redirect("/dispatch/fleet");
}
