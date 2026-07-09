import { redirect } from "next/navigation";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

/** Legacy checkout step → business inquiry. */
export default async function BookContinueRedirectPage({ params }: Props) {
  const { locale } = await params;
  redirect(`/${locale as Locale}/business`);
}
