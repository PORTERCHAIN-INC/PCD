import { redirect } from "next/navigation";
import { publicEnv } from "@/lib/env";
import { customerServerFetch } from "@/lib/server-api";

/**
 * One tracking page: the website's /track/{n}. Signed-in owners get the signed link so
 * receipt, cancel, rating and Send again are unlocked. No duplicate portal tracker.
 */
export default async function TrackOrderRedirect({
  params,
}: {
  params: Promise<{ trackingNumber: string }>;
}) {
  const { trackingNumber } = await params;
  const signed = await customerServerFetch<{ url?: string }>(
    `/v1/customers/me/track-link/${encodeURIComponent(trackingNumber)}`
  );
  const url =
    signed?.url && signed.url.startsWith(publicEnv.websiteUrl)
      ? signed.url
      : `${publicEnv.websiteUrl}/en/track/${encodeURIComponent(trackingNumber)}`;
  redirect(url);
}
