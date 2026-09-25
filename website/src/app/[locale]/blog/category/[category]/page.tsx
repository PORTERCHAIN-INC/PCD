import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing, type Locale } from "@/i18n/routing";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import Container from "@/components/ui/Container";
import ArticleCard from "@/components/blog/ArticleCard";
import BlogSidebar from "@/components/blog/BlogSidebar";
import BlogPagination from "@/components/blog/BlogPagination";
import {
  getPostsByCategory,
  getTrendingPosts,
  getCategoryPostCounts,
  paginatePosts,
} from "@/lib/blog";
import { BLOG_CATEGORIES, isBlogCategory, type BlogCategory } from "@/data/blog-categories";

type Props = {
  params: Promise<{ locale: string; category: string }>;
  searchParams: Promise<{ page?: string }>;
};

export function generateStaticParams() {
  const params: { locale: string; category: string }[] = [];
  for (const locale of routing.locales) {
    for (const category of BLOG_CATEGORIES) {
      params.push({ locale, category });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, category } = await params;
  if (!isBlogCategory(category)) return { title: "Category" };
  const t = await getTranslations({ locale, namespace: "blog" });
  const name = t(`categories.${category}`);
  return {
    title: `${name} | Porterchain Blog`,
    description: `Articles about ${name} from the Porterchain commercial logistics blog.`,
  };
}

export default async function BlogCategoryPage({ params, searchParams }: Props) {
  const { locale, category } = await params;
  const { page: pageParam } = await searchParams;

  if (!isBlogCategory(category)) notFound();

  setRequestLocale(locale);
  const t = await getTranslations("blog.category");
  const tHome = await getTranslations("blog.home");
  const tBlog = await getTranslations("blog");
  const tPag = await getTranslations("blog.pagination");

  const loc = locale as Locale;
  const posts = await getPostsByCategory(loc, category);
  const page = Number(pageParam) || 1;
  const { items, currentPage, totalPages } = paginatePosts(posts, page);

  const trending = await getTrendingPosts(loc);
  const categoryCounts = await getCategoryPostCounts(loc);

  const categoryLabel = (cat: BlogCategory) => tBlog(`categories.${cat}`);
  const readLabel = (minutes: number) => tHome("minRead", { minutes });

  const name = categoryLabel(category);

  return (
    <CorporateShell>
      <section className="pt-28 pb-8 md:pt-32 bg-white border-b border-primary/[0.04]">
        <Container>
          <p className="text-xs font-semibold uppercase tracking-wider text-secondary">
            {t("articlesIn")}
          </p>
          <h1 className="mt-2 text-3xl sm:text-4xl font-semibold text-primary tracking-tight">
            {name}
          </h1>
          <p className="mt-2 text-muted">{t("articleCount", { count: posts.length })}</p>
        </Container>
      </section>

      <section className="site-section bg-gray-bg">
        <Container>
          <div className="grid lg:grid-cols-[1fr_300px] gap-10 lg:gap-12 items-start">
            <div>
              {items.length === 0 ? (
                <p className="text-muted">{tHome("noResults")}</p>
              ) : (
                <div className="grid sm:grid-cols-2 gap-4">
                  {items.map((post) => (
                    <ArticleCard
                      key={post.slug}
                      post={post}
                      categoryLabel={categoryLabel(post.category)}
                      readLabel={readLabel(post.readingMinutes)}
                      locale={locale}
                    />
                  ))}
                </div>
              )}
              <BlogPagination
                currentPage={currentPage}
                totalPages={totalPages}
                basePath={`/blog/category/${category}`}
                previousLabel={tPag("previous")}
                nextLabel={tPag("next")}
                pageLabel={tPag("page", { current: currentPage, total: totalPages })}
              />
            </div>
            <BlogSidebar
              trending={trending}
              categoryCounts={categoryCounts}
              trendingLabel={tHome("trending")}
              categoriesLabel={tBlog("nav.categories")}
              readLabel={readLabel}
              categoryLabel={categoryLabel}
            />
          </div>
        </Container>
      </section>
    </CorporateShell>
  );
}
