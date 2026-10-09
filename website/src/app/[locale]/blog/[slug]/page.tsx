import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing, type Locale } from "@/i18n/routing";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import Container from "@/components/ui/Container";
import MarkdownContent from "@/components/blog/MarkdownContent";
import AuthorCard from "@/components/blog/AuthorCard";
import ShareButtons from "@/components/blog/ShareButtons";
import BlogSidebar, { RelatedPosts } from "@/components/blog/BlogSidebar";
import {
  getAllPostSlugs,
  getPost,
  getRelatedPosts,
  getTrendingPosts,
  getCategoryPostCounts,
} from "@/lib/blog";
import { isBlogCategory, type BlogCategory } from "@/data/blog-categories";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import { buildBlogInternalLinks } from "@/lib/seo/blog-seo";
import { ensureStaticParams } from "@/lib/seo/ensure-static-params";
import InternalLinksBlock from "@/components/seo/InternalLinksBlock";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { resolveBlogCover } from "@/lib/blog";
import { publicEnv } from "@/lib/env";
import { Clock } from "lucide-react";

type Props = { params: Promise<{ locale: string; slug: string }> };

export async function generateStaticParams() {
  const params: { locale: string; slug: string }[] = [];
  for (const locale of routing.locales) {
    for (const slug of await getAllPostSlugs(locale as Locale)) {
      params.push({ locale, slug });
    }
  }
  return ensureStaticParams(params, { locale: routing.locales[0]!, slug: "__build__" });
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const post = await getPost(locale as Locale, slug);
  if (!post) return { title: "Article" };

  return buildPageMetadata(
    locale,
    `blog/${slug}`,
    `${post.title} | Porterchain Blog`,
    post.description
  );
}

export default async function BlogArticlePage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);

  const post = await getPost(locale as Locale, slug);
  if (!post) notFound();

  const t = await getTranslations("blog.article");
  const tHome = await getTranslations("blog.home");
  const tBlog = await getTranslations("blog");

  const loc = locale as Locale;
  const related = await getRelatedPosts(loc, post);
  const trending = await getTrendingPosts(loc);
  const categoryCounts = await getCategoryPostCounts(loc);

  const categoryLabel = (cat: BlogCategory) => tBlog(`categories.${cat}`);
  const readLabel = (minutes: number) => tHome("minRead", { minutes });

  const formattedDate = new Date(post.date).toLocaleDateString(
    locale === "fr" ? "fr-CA" : "en-CA",
    { year: "numeric", month: "long", day: "numeric" }
  );

  const seoLinks = buildBlogInternalLinks(loc, post);

  const siteUrl = publicEnv.siteUrl;
  const articleUrl = `${siteUrl}/${locale}/blog/${slug}`;

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    description: post.description,
    datePublished: post.date,
    author: {
      "@type": "Person",
      name: post.authorId,
    },
  };

  return (
    <CorporateShell>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <article className="pt-28 pb-16 md:pt-32 bg-white">
        <Container>
          <div className="grid lg:grid-cols-[1fr_300px] gap-12 lg:gap-16 items-start">
            <div className="min-w-0">
              <header className="max-w-3xl">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-secondary px-2 py-0.5 rounded-full bg-secondary/10">
                  {categoryLabel(post.category)}
                </span>
                <h1 className="mt-4 text-3xl sm:text-4xl lg:text-[2.75rem] font-semibold text-primary tracking-tight leading-[1.1] text-balance">
                  {post.title}
                </h1>
                <p className="mt-4 text-lg text-muted leading-relaxed">{post.description}</p>
                <div className="mt-6 flex flex-wrap items-center gap-4 text-sm text-muted">
                  <span>
                    {t("published")} <time dateTime={post.date}>{formattedDate}</time>
                  </span>
                  <span className="w-1 h-1 rounded-full bg-primary/20" />
                  <span className="inline-flex items-center gap-1.5">
                    <Clock className="w-4 h-4" aria-hidden />
                    {readLabel(post.readingMinutes)}
                  </span>
                </div>
                <div className="mt-6">
                  <AuthorCard
                    authorId={post.authorId}
                    writtenByLabel={t("writtenBy")}
                    variant="compact"
                  />
                </div>
                <div className="mt-6">
                  <ShareButtons title={post.title} url={articleUrl} />
                </div>
              </header>

              <div className="mt-10 max-w-3xl">
                <HeroPhoto image={resolveBlogCover(post)} aspect="cinematic" priority />
              </div>

              <div className="mt-12 max-w-3xl">
                <MarkdownContent content={post.content} />
              </div>

              {seoLinks.length > 0 && (
                <div className="mt-12 max-w-3xl">
                  <InternalLinksBlock title={t("seoLinksTitle")} links={seoLinks} />
                </div>
              )}

              <div className="mt-12 max-w-3xl">
                <AuthorCard authorId={post.authorId} writtenByLabel={t("writtenBy")} />
              </div>

              <RelatedPosts
                posts={related}
                title={t("related")}
                readLabel={readLabel}
                categoryLabel={categoryLabel}
              />
            </div>

            <BlogSidebar
              trending={trending}
              categoryCounts={categoryCounts}
              trendingLabel={tHome("trending")}
              categoriesLabel={tBlog("nav.categories")}
              readLabel={readLabel}
              categoryLabel={categoryLabel}
              className="hidden lg:block"
            />
          </div>
        </Container>
      </article>
    </CorporateShell>
  );
}
