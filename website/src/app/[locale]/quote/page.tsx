import PortalBookRedirect from "@/lib/portal-book-redirect";

/** Anonymous retail quote → customer portal book funnel (§1.4.1). */
export default function QuoteRedirectPage() {
  return <PortalBookRedirect subpath="book" />;
}
