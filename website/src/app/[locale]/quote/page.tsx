import { redirect } from "next/navigation";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

/** portal-book-redirect — legacy quote funnel → on-site pricing. */
export default async function QuoteRedirectPage({ params }: Props) {
  const { locale } = await params;
  redirect(`/${locale as Locale}/pricing`);
}
