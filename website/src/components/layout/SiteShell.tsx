import { Suspense, type ReactNode } from "react";
import SiteNavbar from "@/components/layout/SiteNavbar";
import SiteFooter from "@/components/layout/SiteFooter";
import PageEnter from "@/components/motion/PageEnter";

export default function SiteShell({ children }: { children: ReactNode }) {
  return (
    <>
      {/* No Suspense/loading boundary here: with cacheComponents, a boundary made the prerendered
          header + page arrive as hidden streamed segments that React reveals ≥300 ms after first
          paint (LCP). The navbar reads only usePathname/useLocale, which prerender statically. */}
      <SiteNavbar />
      <main id="main-content" className="overflow-x-hidden min-w-0">
        <PageEnter>{children}</PageEnter>
      </main>
      {/* The footer is a server component that reads the request locale. Pages that call
          setRequestLocale prerender it into the static shell; pages that resolve the locale
          inside their own Suspense (track, not-found) stream it after. Below the fold either way. */}
      <Suspense fallback={null}>
        <SiteFooter />
      </Suspense>
    </>
  );
}
