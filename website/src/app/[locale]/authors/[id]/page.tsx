import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import Container from "@/components/ui/Container";
import ArticleCard from "@/components/blog/ArticleCard";
import { blogAuthors, getAuthor } from "@/data/blog-authors";
import { getAllPosts } from "@/lib/blog";
import type { BlogCategory } from "@/data/blog-categories";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string; id: string }> };

export function generateStaticParams() {
  const ids = Object.keys(blogAuthors);
  return routing.locales.flatMap((locale) => ids.map((id) => ({ locale, id })));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, id } = await params;
  if (!blogAuthors[id]) return {};
  const author = getAuthor(id);
  const t = await getTranslations({ locale, namespace: "authors" });
  return buildPageMetadata(
    locale,
    `authors/${id}`,
    t("profile.metaTitle", { name: author.name }),
    t("profile.metaDescription", { name: author.name, role: author.role })
  );
}

export default async function AuthorProfilePage({ params }: Props) {
  const { locale, id } = await params;
  if (!blogAuthors[id]) notFound();
  setRequestLocale(locale);

  const t = await getTranslations("authors");
  const tBlog = await getTranslations("blog");
  const tHome = await getTranslations("blog.home");
  const author = getAuthor(id);
  const loc = locale as Locale;
  const posts = (await getAllPosts(loc)).filter((p) => p.authorId === id);
  const initials = author.name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2);
  const categoryLabel = (cat: BlogCategory) => tBlog(`categories.${cat}`);
  const readLabel = (minutes: number) => tHome("minRead", { minutes });

  return (
    <CorporateShell>
      <section className="border-b border-primary/[0.04] bg-white pt-28 pb-12 md:pt-32">
        <Container>
          <Link href="/authors" className="text-sm font-semibold text-secondary hover:underline">
            ← {t("profile.back")}
          </Link>
          <div className="mt-8 flex flex-col gap-6 sm:flex-row sm:items-start">
            <div
              className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-secondary text-xl font-semibold text-white"
              aria-hidden
            >
              {initials}
            </div>
            <div className="max-w-2xl">
              <h1 className="text-3xl font-semibold tracking-tight text-primary sm:text-4xl">
                {author.name}
              </h1>
              <p className="mt-2 text-base font-medium text-secondary">{author.role}</p>
              <p className="mt-4 text-base leading-relaxed text-muted">{author.bio}</p>
            </div>
          </div>
        </Container>
      </section>

      <section className="bg-gray-bg py-14">
        <Container>
          <h2 className="text-xl font-semibold text-primary">{t("profile.postsTitle")}</h2>
          {posts.length === 0 ? (
            <p className="mt-4 text-sm text-muted">{t("profile.noPosts")}</p>
          ) : (
            <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {posts.map((post) => (
                <ArticleCard
                  key={post.slug}
                  post={post}
                  categoryLabel={categoryLabel(post.category)}
                  readLabel={readLabel(post.readingMinutes)}
                  locale={loc}
                />
              ))}
            </div>
          )}
        </Container>
      </section>
    </CorporateShell>
  );
}
