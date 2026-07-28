import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";

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
                href={link.href}
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
