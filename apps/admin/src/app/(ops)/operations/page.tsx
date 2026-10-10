import { redirect } from "next/navigation";
import { legacyOperationsTarget } from "@/lib/dispatch";

/** Control Tower moved to Dispatch. Old ?view=/&tool= links land on the matching section. */
export default async function OperationsRedirect({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? null;
  redirect(legacyOperationsTarget(one(sp.view), one(sp.tool)));
}
