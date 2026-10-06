import type { ReactNode } from "react";

/** Optional catch-all Clerk steps — request-time URL segments. */
export const instant = false;

export default function SignUpCatchAllLayout({ children }: { children: ReactNode }) {
  return children;
}
