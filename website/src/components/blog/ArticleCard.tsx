import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { Clock, ArrowUpRight } from "lucide-react";
import SiteImage from "@/components/ui/SiteImage";
import type { BlogPostMeta } from "@/lib/blog-meta";
import { resolveBlogCover } from "@/lib/blog-meta";
import type { BlogCategory } from "@/data/blog-categories";

interface ArticleCardProps {
  post: BlogPostMeta;
  categoryLabel: string;
  readLabel: string;
  variant?: "default" | "compact" | "horizontal";
  className?: string;
  locale?: string;
}

function formatDate(date: string, locale: string) {
  return new Date(date).toLocaleDateString(locale === "fr" ? "fr-CA" : "en-CA", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function ArticleCard({
  post,
  categoryLabel,
  readLabel,
  variant = "default",
  className,
  locale = "en",
}: ArticleCardProps) {
  if (variant === "horizontal") {
    const cover = resolveBlogCover(post);
    return (
      <Link
        href={`/blog/${post.slug}`}
        className={cn(
          "group flex flex-col sm:flex-row gap-4 sm:gap-6 p-5 rounded-2xl border border-primary/[0.06] bg-white hover:border-secondary/20 hover:shadow-lg hover:shadow-secondary/5 transition-all overflow-hidden",
          className
        )}
      >
        <div className="relative w-full sm:w-40 h-32 sm:h-auto sm:min-h-[120px] shrink-0 rounded-xl overflow-hidden">
          <SiteImage
            image={cover}
            fill
            className="object-cover group-hover:scale-[1.02] transition-transform duration-500"
            sizes="(max-width: 640px) 100vw, 200px"
          />
        </div>
        <div className="flex-1 min-w-0">
          <CategoryPill label={categoryLabel} />
          <h3 className="mt-2 text-lg font-semibold text-primary tracking-tight group-hover:text-secondary transition-colors line-clamp-2">
            {post.title}
          </h3>
          <p className="mt-2 text-sm text-muted leading-relaxed line-clamp-2">{post.description}</p>
          <CardMeta
            date={post.date}
            minutes={post.readingMinutes}
            readLabel={readLabel}
            locale={locale}
          />
        </div>
        <ArrowUpRight className="w-5 h-5 text-secondary opacity-0 group-hover:opacity-100 transition-opacity shrink-0 hidden sm:block" />
      </Link>
    );
  }

  const cover = resolveBlogCover(post);

  return (
    <Link
      href={`/blog/${post.slug}`}
      className={cn(
        "group flex flex-col h-full rounded-2xl border border-primary/[0.06] bg-white overflow-hidden hover:border-secondary/20 hover:shadow-lg hover:shadow-secondary/5 transition-all",
        className
      )}
    >
      <div className="relative h-40 overflow-hidden">
        <SiteImage
          image={cover}
          fill
          className="object-cover group-hover:scale-[1.03] transition-transform duration-500"
          sizes="(max-width: 640px) 100vw, 33vw"
        />
      </div>
      <div className="p-5 sm:p-6 flex flex-col flex-1">
        <CategoryPill label={categoryLabel} />
        <h3
          className={cn(
            "mt-3 font-semibold text-primary tracking-tight group-hover:text-secondary transition-colors",
            variant === "compact" ? "text-base line-clamp-2" : "text-lg line-clamp-3"
          )}
        >
          {post.title}
        </h3>
        {variant !== "compact" && (
          <p className="mt-2 text-sm text-muted leading-relaxed line-clamp-3 flex-1">
            {post.description}
          </p>
        )}
        <CardMeta
          date={post.date}
          minutes={post.readingMinutes}
          readLabel={readLabel}
          locale={locale}
          className="mt-4"
        />
      </div>
    </Link>
  );
}

function CategoryPill({ label }: { label: string }) {
  return (
    <span className="inline-block text-[10px] font-semibold uppercase tracking-wider text-secondary px-2 py-0.5 rounded-full bg-secondary/10">
      {label}
    </span>
  );
}

function CardMeta({
  date,
  minutes,
  readLabel,
  locale,
  className,
}: {
  date: string;
  minutes: number;
  readLabel: string;
  locale: string;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-3 text-xs text-muted", className)}>
      <time dateTime={date}>{formatDate(date, locale)}</time>
      <span className="w-1 h-1 rounded-full bg-primary/20" />
      <span className="inline-flex items-center gap-1">
        <Clock className="w-3 h-3" aria-hidden />
        {readLabel}
      </span>
    </div>
  );
}

export function FeaturedArticleCard({
  post,
  categoryLabel,
  readLabel,
  featuredLabel,
  ctaLabel,
}: {
  post: BlogPostMeta;
  categoryLabel: string;
  readLabel: string;
  featuredLabel: string;
  ctaLabel: string;
}) {
  const cover = resolveBlogCover(post);

  return (
    <Link
      href={`/blog/${post.slug}`}
      className="group block rounded-2xl border border-primary/[0.06] bg-white overflow-hidden hover:shadow-xl hover:shadow-secondary/10 transition-all"
    >
      <div className="grid lg:grid-cols-2">
        <div className="relative min-h-[280px] lg:min-h-[360px] overflow-hidden">
          <SiteImage
            image={cover}
            fill
            className="object-cover group-hover:scale-[1.02] transition-transform duration-500"
            sizes="(max-width: 1024px) 100vw, 50vw"
            priority
          />
          <div className="absolute inset-0 bg-gradient-to-t from-primary/80 via-primary/30 to-transparent" />
          <div className="absolute bottom-6 left-6 right-6">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-secondary">
              {featuredLabel}
            </span>
            <span className="ml-2 text-[10px] font-semibold uppercase tracking-wider text-white/70">
              {categoryLabel}
            </span>
          </div>
        </div>
        <div className="p-8 sm:p-10 lg:p-12 flex flex-col justify-center">
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-semibold text-primary tracking-tight leading-[1.12] group-hover:text-secondary transition-colors text-balance">
            {post.title}
          </h2>
          <p className="mt-4 text-muted leading-relaxed line-clamp-3">{post.description}</p>
          <div className="mt-6 flex items-center gap-4">
            <span className="inline-flex items-center gap-1.5 text-sm text-muted">
              <Clock className="w-4 h-4" aria-hidden />
              {readLabel}
            </span>
            <span className="text-sm font-semibold text-secondary group-hover:underline underline-offset-4">
              {ctaLabel} →
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}

export function categoryLabelFor(t: (key: string) => string, category: BlogCategory): string {
  return t(`categories.${category}`);
}
