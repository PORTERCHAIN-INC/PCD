import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import type { BlogCategory } from "@/data/blog-categories";

interface CategoryPillsProps {
  categories: BlogCategory[];
  counts: Record<BlogCategory, number>;
  label: (cat: BlogCategory) => string;
  title: string;
  className?: string;
}

export default function CategoryPills({
  categories,
  counts,
  label,
  title,
  className,
}: CategoryPillsProps) {
  return (
    <section className={cn("", className)}>
      <h2 className="text-sm font-semibold uppercase tracking-wider text-muted mb-4">{title}</h2>
      <div className="flex flex-wrap gap-2">
        {categories.map((cat) =>
          counts[cat] > 0 ? (
            <Link
              key={cat}
              href={`/blog/category/${cat}`}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium bg-white border border-primary/[0.08] text-primary/80 hover:border-secondary/30 hover:text-secondary hover:bg-secondary/5 transition-all"
            >
              {label(cat)}
              <span className="text-xs text-muted tabular-nums">{counts[cat]}</span>
            </Link>
          ) : null
        )}
      </div>
    </section>
  );
}
