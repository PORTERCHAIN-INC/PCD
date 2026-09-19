import { redirect } from "next/navigation";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

/** Legacy slug → Vehicle Partner Portal landing page. */
export default async function DriveRedirectPage({ params }: Props) {
  const { locale } = await params;
  redirect(`/${locale as Locale}/vehicle-partner`);
}
