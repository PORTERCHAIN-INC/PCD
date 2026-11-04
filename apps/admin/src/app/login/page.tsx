import { redirect } from "next/navigation";

// L169: /login is a common guess (and the driver portal uses it). Signed-in users got a 404 here.
export default async function LoginAlias({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(await searchParams)) if (typeof v === "string") sp.set(k, v);
  const q = sp.toString();
  redirect(q ? `/sign-in?${q}` : "/sign-in");
}
