import { redirect } from "next/navigation";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

/** Legacy retail `/book` → B2B business inquiry (customer portal book is not linked from marketing). */
export default async function BookRedirectPage({ params }: Props) {
  const { locale } = await params;
  redirect(`/${locale as Locale}/business`);
}
