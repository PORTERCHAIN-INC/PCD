import { redirect } from "next/navigation";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

/** portal-book-redirect — legacy confirmation → on-site contact (quote intent). */
export default async function BookSuccessRedirectPage({ params }: Props) {
  const { locale } = await params;
  redirect(`/${locale as Locale}/contact?intent=quote&from=book-success`);
}
