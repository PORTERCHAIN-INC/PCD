import { Suspense, type ReactNode } from "react";
import SiteNavbar from "@/components/layout/SiteNavbar";
import SiteFooter from "@/components/layout/SiteFooter";
import PageEnter from "@/components/motion/PageEnter";

function NavbarFallback() {
  return <div className="h-16 w-full border-b border-primary/5 bg-white" aria-hidden />;
}

export default function SiteShell({ children }: { children: ReactNode }) {
  return (
    <>
      <Suspense fallback={<NavbarFallback />}>
        <SiteNavbar />
      </Suspense>
      <main id="main-content" className="overflow-x-hidden min-w-0">
        <PageEnter>{children}</PageEnter>
      </main>
      <SiteFooter />
    </>
  );
}
