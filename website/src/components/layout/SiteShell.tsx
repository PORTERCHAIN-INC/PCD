import type { ReactNode } from "react";
import SiteNavbar from "@/components/layout/SiteNavbar";
import SiteFooter from "@/components/layout/SiteFooter";
import PageEnter from "@/components/motion/PageEnter";

export default function SiteShell({ children }: { children: ReactNode }) {
  return (
    <>
      <SiteNavbar />
      <main id="main-content" className="overflow-x-hidden min-w-0">
        <PageEnter>{children}</PageEnter>
      </main>
      <SiteFooter />
    </>
  );
}
