"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { useTranslations } from "next-intl";
import ArticleCard, { categoryLabelFor } from "@/components/blog/ArticleCard";
import type { BlogPostMeta } from "@/lib/blog-meta";

interface BlogSearchProps {
  posts: BlogPostMeta[];
}

export default function BlogSearch({ posts }: BlogSearchProps) {
  const t = useTranslations("blog.home");
  const tCat = useTranslations("blog");
  const [query, setQuery] = useState("");

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return posts.filter(
      (p) =>
        p.title.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q) ||
        p.tags?.some((tag) => tag.toLowerCase().includes(q))
    );
  }, [posts, query]);

  return (
    <div className="relative">
      <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted pointer-events-none" />
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={t("searchPlaceholder")}
        aria-label={t("searchPlaceholder")}
        className="w-full pl-11 pr-4 py-3 rounded-full border border-primary/10 bg-white text-sm text-primary outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/15 transition-shadow"
      />
      {query.trim() && (
        <div className="absolute z-20 top-full left-0 right-0 mt-2 rounded-2xl border border-primary/[0.06] bg-white shadow-xl max-h-96 overflow-y-auto p-2">
          {results.length === 0 ? (
            <p className="px-4 py-6 text-sm text-muted text-center">{t("noResults")}</p>
          ) : (
            results
              .slice(0, 6)
              .map((post) => (
                <ArticleCard
                  key={post.slug}
                  post={post}
                  categoryLabel={categoryLabelFor(tCat, post.category)}
                  readLabel={t("minRead", { minutes: post.readingMinutes })}
                  variant="horizontal"
                  className="border-0 shadow-none hover:shadow-none mb-1"
                />
              ))
          )}
        </div>
      )}
    </div>
  );
}
