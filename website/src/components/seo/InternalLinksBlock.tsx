import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import { routing } from "@/i18n/routing";

const LOCALE_PREFIX = new RegExp(`^/(?:${routing.locales.join("|")})(?=/|\\?|#|$)`);

/**
 * Builders return locale-prefixed paths (/en/faq/x?from=business). The locale-aware Link
 * prefixes again when the href carries a query string, producing /en/en/... 404s
 * (readiness audit #14). Strip the prefix and let Link add the active locale once.
 */
export function unprefixLocale(href: string): string {
  if (!href.startsWith("/")) return href;
  const stripped = href.replace(LOCALE_PREFIX, "");
  return stripped === "" ? "/" : stripped.startsWith("/") ? stripped : `/${stripped}`;
}

interface InternalLinksBlockProps {
  title: string;
  links: { href: string; label: string }[];
}

export default function InternalLinksBlock({ title, links }: InternalLinksBlockProps) {
  if (!links.length) return null;
  return (
    <section className="py-10 md:py-12 bg-gray-bg border-y border-primary/[0.04]">
      <Container size="narrow">
        <h2 className="text-xl font-semibold text-primary tracking-tight">{title}</h2>
        <ul className="mt-4 grid sm:grid-cols-2 gap-2.5">
          {links.map((link) => (
            <li key={link.href}>
              <Link
                href={unprefixLocale(link.href)}
                className="text-secondary hover:text-primary font-medium transition-colors"
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}
