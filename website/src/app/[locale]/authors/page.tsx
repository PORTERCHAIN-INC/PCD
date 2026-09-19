import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import Container from "@/components/ui/Container";
import { blogAuthors } from "@/data/blog-authors";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "authors" });
  return buildPageMetadata(locale, "authors", t("meta.title"), t("meta.description"));
}

export default async function AuthorsHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("authors");
  const authors = Object.values(blogAuthors);

  return (
    <CorporateShell>
      <section className="border-b border-primary/[0.04] bg-white pt-28 pb-14 md:pt-32">
        <Container>
          <div className="mx-auto max-w-3xl text-center">
            <p className="text-xs font-semibold uppercase tracking-wider text-secondary">
              {t("hub.eyebrow")}
            </p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-primary sm:text-5xl">
              {t("hub.title")}
            </h1>
            <p className="mt-4 text-lg leading-relaxed text-muted">{t("hub.subtitle")}</p>
          </div>

          <ul className="mx-auto mt-12 grid max-w-4xl gap-6 sm:grid-cols-3">
            {authors.map((author) => {
              const initials = author.name
                .split(" ")
                .map((n) => n[0])
                .join("")
                .slice(0, 2);
              return (
                <li key={author.id}>
                  <Link
                    href={`/authors/${author.id}`}
                    className="block h-full rounded-2xl border border-primary/[0.06] bg-gray-bg p-6 transition-colors hover:border-secondary/30"
                  >
                    <div
                      className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary text-base font-semibold text-white"
                      aria-hidden
                    >
                      {initials}
                    </div>
                    <h2 className="mt-4 text-lg font-semibold text-primary">{author.name}</h2>
                    <p className="mt-1 text-sm text-secondary">{author.role}</p>
                    <p className="mt-3 text-sm leading-relaxed text-muted">{author.bio}</p>
                    <span className="mt-4 inline-flex text-sm font-semibold text-secondary">
                      {t("hub.viewProfile")} →
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </Container>
      </section>
    </CorporateShell>
  );
}
