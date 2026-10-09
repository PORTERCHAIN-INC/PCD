import { notFound } from "next/navigation";
import { routing } from "@/i18n/routing";

/** Unknown URLs under a locale get the designed [locale]/not-found page (404), not Next's bare one. */
export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale, rest: ["__build__"] }));
}

export default function UnknownPage() {
  notFound();
}
