import PortalBookRedirect from "@/lib/portal-book-redirect";

/** Legacy checkout URL → customer portal book funnel (§1.4.1). */
export default function BookContinueRedirectPage() {
  return <PortalBookRedirect subpath="book" />;
}
