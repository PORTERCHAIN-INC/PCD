import type { ReactNode } from "react";
import SiteNavbar from "@/components/layout/SiteNavbar";
import SiteFooter from "@/components/layout/SiteFooter";

export default function SiteShell({ children }: { children: ReactNode }) {
  return (
    <>
      <SiteNavbar />
      <main className="overflow-x-hidden">{children}</main>
      <SiteFooter />
    </>
  );
}
