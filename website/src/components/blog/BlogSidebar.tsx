import { Link } from "@/i18n/navigation";
import BlogNewsletter from "@/components/blog/BlogNewsletter";
import ArticleCard from "@/components/blog/ArticleCard";
import type { BlogPostMeta } from "@/lib/blog-meta";
import type { BlogCategory } from "@/data/blog-categories";
import { BLOG_CATEGORIES } from "@/data/blog-categories";
import { cn } from "@/lib/utils";

interface BlogSidebarProps {
  trending: BlogPostMeta[];
  categoryCounts: Record<BlogCategory, number>;
  trendingLabel: string;
  categoriesLabel: string;
  readLabel: (minutes: number) => string;
  categoryLabel: (cat: BlogCategory) => string;
  className?: string;
}

export default function BlogSidebar({
  trending,
  categoryCounts,
  trendingLabel,
  categoriesLabel,
  readLabel,
  categoryLabel,
  className,
}: BlogSidebarProps) {
  const popular = [...BLOG_CATEGORIES]
    .sort((a, b) => categoryCounts[b] - categoryCounts[a])
    .filter((c) => categoryCounts[c] > 0);

  return (
    <aside className={cn("space-y-6 lg:sticky lg:top-24 lg:self-start", className)}>
      <BlogNewsletter />

      <div className="rounded-2xl border border-primary/[0.06] bg-white p-5">
        <h3 className="text-sm font-semibold text-primary tracking-tight">{trendingLabel}</h3>
        <ol className="mt-4 space-y-4">
          {trending.map((post, i) => (
            <li key={post.slug}>
              <Link href={`/blog/${post.slug}`} className="group block">
                <span className="text-xs font-bold text-secondary">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <p className="mt-1 text-sm font-medium text-primary group-hover:text-secondary transition-colors line-clamp-2 leading-snug">
                  {post.title}
                </p>
                <p className="mt-1 text-xs text-muted">{readLabel(post.readingMinutes)}</p>
              </Link>
            </li>
          ))}
        </ol>
      </div>

      <div className="rounded-2xl border border-primary/[0.06] bg-white p-5">
        <h3 className="text-sm font-semibold text-primary tracking-tight">{categoriesLabel}</h3>
        <ul className="mt-4 space-y-1">
          {popular.map((cat) => (
            <li key={cat}>
              <Link
                href={`/blog/category/${cat}`}
                className="flex items-center justify-between py-2 px-2 -mx-2 rounded-lg text-sm text-primary/80 hover:text-secondary hover:bg-gray-bg transition-colors"
              >
                <span>{categoryLabel(cat)}</span>
                <span className="text-xs text-muted tabular-nums">{categoryCounts[cat]}</span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}

export function RelatedPosts({
  posts,
  title,
  readLabel,
  categoryLabel,
}: {
  posts: BlogPostMeta[];
  title: string;
  readLabel: (minutes: number) => string;
  categoryLabel: (cat: BlogCategory) => string;
}) {
  if (posts.length === 0) return null;

  return (
    <section className="mt-16 pt-12 border-t border-primary/[0.06]">
      <h2 className="text-xl font-semibold text-primary tracking-tight mb-6">{title}</h2>
      <div className="grid sm:grid-cols-3 gap-4">
        {posts.map((post) => (
          <ArticleCard
            key={post.slug}
            post={post}
            categoryLabel={categoryLabel(post.category)}
            readLabel={readLabel(post.readingMinutes)}
            variant="compact"
          />
        ))}
      </div>
    </section>
  );
}
