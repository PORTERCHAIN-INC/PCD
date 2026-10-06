import type { Metadata } from "next";
import { Suspense } from "react";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing, type Locale } from "@/i18n/routing";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import Container from "@/components/ui/Container";
import BlogSearch from "@/components/blog/BlogSearch";
import ArticleCard, { FeaturedArticleCard } from "@/components/blog/ArticleCard";
import BlogSidebar from "@/components/blog/BlogSidebar";
import CategoryPills from "@/components/blog/CategoryPills";
import BlogPagination from "@/components/blog/BlogPagination";
import {
  getAllPosts,
  getFeaturedPost,
  getTrendingPosts,
  getCategoryPostCounts,
  paginatePosts,
  POSTS_PER_PAGE,
} from "@/lib/blog";
import { BLOG_CATEGORIES } from "@/data/blog-categories";
import type { BlogCategory } from "@/data/blog-categories";
import { buildPageMetadata } from "@/lib/seo/page-helpers";

type Props = {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ page?: string }>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "blog.metadata" });
  return buildPageMetadata(locale, "blog", t("title"), t("description"));
}

async function BlogHomeBody({
  locale,
  searchParams,
}: {
  locale: string;
  searchParams: Promise<{ page?: string }>;
}) {
  const { page: pageParam } = await searchParams;
  const t = await getTranslations("blog.home");
  const tBlog = await getTranslations("blog");
  const tPag = await getTranslations("blog.pagination");

  const loc = locale as Locale;
  const allPosts = await getAllPosts(loc);
  const featured = await getFeaturedPost(loc);
  const trending = await getTrendingPosts(loc);
  const categoryCounts = await getCategoryPostCounts(loc);

  const latestPool = featured ? allPosts.filter((p) => p.slug !== featured.slug) : allPosts;

  const page = Number(pageParam) || 1;
  const {
    items: latest,
    currentPage,
    totalPages,
  } = paginatePosts(latestPool, page, POSTS_PER_PAGE);

  const categoryLabel = (cat: BlogCategory) => tBlog(`categories.${cat}`);
  const readLabel = (minutes: number) => t("minRead", { minutes });

  return (
    <>
      <section className="pt-28 pb-10 md:pt-32 md:pb-14 bg-white border-b border-primary/[0.04]">
        <Container>
          <div className="max-w-3xl">
            <span className="text-xs font-semibold uppercase tracking-wider text-secondary">
              {t("badge")}
            </span>
            <h1 className="mt-3 text-4xl sm:text-5xl font-semibold text-primary tracking-tight text-balance leading-[1.08]">
              {t("title")}
            </h1>
            <p className="mt-4 text-lg text-muted leading-relaxed">{t("subtitle")}</p>
          </div>
          <div className="mt-8 max-w-xl">
            <BlogSearch posts={allPosts} />
          </div>
        </Container>
      </section>

      <section className="site-section bg-gray-bg">
        <Container>
          {featured && (
            <div className="mb-12">
              <FeaturedArticleCard
                post={featured}
                categoryLabel={categoryLabel(featured.category)}
                readLabel={readLabel(featured.readingMinutes)}
                featuredLabel={t("featured")}
                ctaLabel={t("readArticle")}
              />
            </div>
          )}

          <CategoryPills
            categories={[...BLOG_CATEGORIES]}
            counts={categoryCounts}
            label={categoryLabel}
            title={t("popularCategories")}
            className="mb-12"
          />

          <div className="grid lg:grid-cols-[1fr_320px] gap-10 lg:gap-12 items-start">
            <div>
              <h2 className="text-xl font-semibold text-primary tracking-tight mb-6">
                {t("latest")}
              </h2>
              <div className="grid sm:grid-cols-2 gap-4">
                {latest.map((post) => (
                  <ArticleCard
                    key={post.slug}
                    post={post}
                    categoryLabel={categoryLabel(post.category)}
                    readLabel={readLabel(post.readingMinutes)}
                    locale={locale}
                  />
                ))}
              </div>
              <BlogPagination
                currentPage={currentPage}
                totalPages={totalPages}
                basePath="/blog"
                previousLabel={tPag("previous")}
                nextLabel={tPag("next")}
                pageLabel={tPag("page", { current: currentPage, total: totalPages })}
              />
            </div>

            <BlogSidebar
              trending={trending}
              categoryCounts={categoryCounts}
              trendingLabel={t("trending")}
              categoriesLabel={tBlog("nav.categories")}
              readLabel={readLabel}
              categoryLabel={categoryLabel}
            />
          </div>
        </Container>
      </section>
    </>
  );
}

export default async function BlogHomePage({ params, searchParams }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <CorporateShell>
      <Suspense
        fallback={
          <section className="site-section bg-gray-bg">
            <Container>
              <p className="text-sm text-muted">Loading blog…</p>
            </Container>
          </section>
        }
      >
        <BlogHomeBody locale={locale} searchParams={searchParams} />
      </Suspense>
    </CorporateShell>
  );
}
