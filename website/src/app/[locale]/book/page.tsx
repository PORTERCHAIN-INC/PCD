import { redirect } from "next/navigation";
import { routing } from "@/i18n/routing";
import { customerPortalBookUrl } from "@/data/portal-links";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

/** portal-book-redirect — legacy marketing `/book` → customer portal retail funnel (:3004). */
export default async function BookRedirectPage({ params }: Props) {
  await params;
  redirect(customerPortalBookUrl);
}
