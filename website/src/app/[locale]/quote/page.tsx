import { redirect } from "next/navigation";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

/** Legacy /quote — marketing CTA only; book on customer portal after sign-up. */
export default async function QuoteRedirectPage({ params }: Props) {
  const { locale } = await params;
  redirect(`/${locale as Locale}/sign-up?intent=quote&from=quote`);
}
