import { notFound } from "next/navigation";
import { localeStaticParams } from "@/lib/seo/page-helpers";

/**
 * Rewrite target for URLs the middleware already knows are dead (url-policy "notfound" and
 * unknown programmatic slugs). It only throws notFound(), so the visitor gets the designed
 * [locale]/not-found page with a real 404 status. (The old `__not-found__` target was a
 * private folder name in the App Router, so it fell through to Next's bare default 404.)
 */
export const generateStaticParams = localeStaticParams;

export default function PageNotFound() {
  notFound();
}
