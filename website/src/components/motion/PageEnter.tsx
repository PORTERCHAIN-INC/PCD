/**
 * Subtle page mount motion for SiteShell content (all routes).
 *
 * Server component + CSS only (Core Web Vitals): the old framer-motion version started every
 * page at `opacity: 0` until hydration, so LCP waited for ~600 KB of JS. This one only moves
 * 6px (opacity stays 1, content is visible on first paint) and is skipped under
 * `prefers-reduced-motion` — see `.page-enter` in globals.css.
 */
export default function PageEnter({ children }: { children: React.ReactNode }) {
  return <div className="page-enter">{children}</div>;
}
