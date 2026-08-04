import { redirect } from "next/navigation";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

/** Legacy /quote — capacity CTA lands on the business inquiry form. */
export default async function QuoteRedirectPage({ params }: Props) {
  const { locale } = await params;
  redirect(`/${locale as Locale}/business?from=quote#inquiry`);
}
