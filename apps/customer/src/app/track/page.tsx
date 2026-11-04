import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { publicEnv } from "@/lib/env";
import { readLocaleCookie } from "@/i18n/core";

/** Tracking lookup lives on the public website (no login); keep the user's language. */
export default async function TrackLookupRedirect() {
  const jar = await cookies();
  const locale = readLocaleCookie(jar.toString());
  redirect(`${publicEnv.websiteUrl}/${locale}/track`);
}
