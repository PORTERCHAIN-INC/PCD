import { ArrowRight } from "lucide-react";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";

/** Closing call-to-action band shared by home, calculator and /delivery pages. */
export default function CtaBand({
  id,
  title,
  body,
  primary,
  secondary,
  children,
}: {
  id: string;
  title: string;
  body?: string;
  /** `href` starting with "#" renders a same-page anchor. */
  primary: { href: string; label: string };
  secondary?: { href: string; label: string };
  children?: React.ReactNode;
}) {
  const primaryClass =
    "inline-flex min-h-[var(--touch-min)] items-center justify-center gap-2 rounded-full bg-secondary px-6 py-3 text-base font-semibold text-white shadow-lg shadow-secondary/25 transition-[background-color,transform] hover:bg-[#1a47bf] motion-safe:hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary";
  const secondaryClass =
    "inline-flex min-h-[var(--touch-min)] items-center justify-center gap-2 rounded-full border border-white/30 px-6 py-3 text-base font-semibold text-white transition-colors hover:border-white/60 hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white";
  return (
    <section
      className="relative isolate overflow-hidden bg-primary text-white"
      aria-labelledby={id}
    >
      <div
        className="pointer-events-none absolute -right-24 -top-32 -z-10 h-[28rem] w-[28rem] rounded-full bg-secondary/30 blur-3xl"
        aria-hidden
      />
      <Container className="flex flex-col gap-8 py-16 sm:py-20 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-xl">
          <h2 id={id} className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            {title}
          </h2>
          {body ? <p className="mt-3 text-lg leading-relaxed text-white/75">{body}</p> : null}
          {children ? <div className="mt-5">{children}</div> : null}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {primary.href.startsWith("#") ? (
            <a href={primary.href} className={primaryClass}>
              {primary.label}
              <ArrowRight className="h-4 w-4" aria-hidden />
            </a>
          ) : (
            <Link href={primary.href} className={primaryClass}>
              {primary.label}
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          )}
          {secondary ? (
            <Link href={secondary.href} className={secondaryClass}>
              {secondary.label}
            </Link>
          ) : null}
        </div>
      </Container>
    </section>
  );
}
