import { Link } from "@/i18n/navigation";
import { ChevronRight } from "lucide-react";
import Container from "@/components/ui/Container";

export type BreadcrumbItem = { label: string; href?: string };

interface PageBreadcrumbsProps {
  items: BreadcrumbItem[];
  /** "dark" renders inline inside a dark hero (no bar, no nav offset — the hero handles it). */
  tone?: "light" | "dark";
}

export default function PageBreadcrumbs({ items, tone = "light" }: PageBreadcrumbsProps) {
  if (items.length === 0) return null;

  if (tone === "dark") {
    return (
      <nav aria-label="Breadcrumb">
        <ol className="flex flex-wrap items-center gap-1.5 text-sm text-white/70">
          {items.map((item, index) => (
            <li key={`${item.label}-${index}`} className="flex items-center gap-1.5">
              {index > 0 && (
                <ChevronRight className="w-3.5 h-3.5 shrink-0 opacity-60" aria-hidden />
              )}
              {item.href ? (
                <Link
                  href={item.href}
                  className="rounded hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
                >
                  {item.label}
                </Link>
              ) : (
                <span className="text-white font-medium line-clamp-1" aria-current="page">
                  {item.label}
                </span>
              )}
            </li>
          ))}
        </ol>
      </nav>
    );
  }

  return (
    <nav aria-label="Breadcrumb" className="border-b border-primary/[0.06] bg-white">
      <Container className="py-3 pt-[4.5rem] md:pt-[4.75rem]">
        <ol className="flex flex-wrap items-center gap-1.5 text-sm text-muted">
          {items.map((item, index) => (
            <li key={`${item.label}-${index}`} className="flex items-center gap-1.5">
              {index > 0 && (
                <ChevronRight className="w-3.5 h-3.5 shrink-0 opacity-50" aria-hidden />
              )}
              {item.href ? (
                <Link href={item.href} className="hover:text-primary transition-colors">
                  {item.label}
                </Link>
              ) : (
                <span className="text-primary font-medium line-clamp-1" aria-current="page">
                  {item.label}
                </span>
              )}
            </li>
          ))}
        </ol>
      </Container>
    </nav>
  );
}
