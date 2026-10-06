"use client";

import { usePathname } from "next/navigation";
import { NavDropdown as SharedNavDropdown } from "@porterchain/ui/nav-dropdown";
import type { ComponentProps } from "react";

export default function NavDropdown(
  props: Omit<ComponentProps<typeof SharedNavDropdown>, "closeOnNavigate">
) {
  const pathname = usePathname();
  return <SharedNavDropdown {...props} closeOnNavigate={pathname} />;
}
