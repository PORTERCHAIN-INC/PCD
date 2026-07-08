import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";

interface InternalLinksBlockProps {
  title: string;
  links: { href: string; label: string }[];
}

export default function InternalLinksBlock({ title, links }: InternalLinksBlockProps) {
  if (!links.length) return null;
  return (
    <section className="site-section bg-gray-bg">
      <Container size="narrow">
        <h2 className="text-2xl font-semibold text-primary tracking-tight">{title}</h2>
        <ul className="mt-6 grid sm:grid-cols-2 gap-3">
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
