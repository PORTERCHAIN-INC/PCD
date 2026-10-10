import { redirect } from "next/navigation";
import { publicEnv } from "@/lib/env";

/** Tracking lookup lives on the public website (no login). */
export default function TrackLookupRedirect() {
  redirect(`${publicEnv.websiteUrl}/en/track`);
}
