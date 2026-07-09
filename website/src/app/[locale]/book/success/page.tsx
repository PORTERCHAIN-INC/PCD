import PortalBookRedirect from "@/lib/portal-book-redirect";

/** Stripe return URL legacy path → customer portal success (§1.4.1). */
export default function BookSuccessRedirectPage() {
  return <PortalBookRedirect subpath="book/success" />;
}
