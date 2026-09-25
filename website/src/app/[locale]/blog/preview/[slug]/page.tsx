import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import Container from "@/components/ui/Container";
import MarkdownContent from "@/components/blog/MarkdownContent";
import { getPreviewPost } from "@/lib/blog";
import type { Locale } from "@/i18n/routing";

type Props = {
  params: Promise<{ locale: string; slug: string }>;
  searchParams: Promise<{ token?: string }>;
};

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  return {
    title: `Preview · ${slug}`,
    robots: { index: false, follow: false },
  };
}

export default async function BlogPreviewPage({ params, searchParams }: Props) {
  const { locale, slug } = await params;
  const { token } = await searchParams;
  setRequestLocale(locale);

  if (!token?.trim()) notFound();

  const post = await getPreviewPost(locale as Locale, slug, token.trim());
  if (!post) notFound();

  return (
    <CorporateShell>
      <section className="border-b border-amber-500/30 bg-amber-50 py-3">
        <Container>
          <p className="text-center text-sm font-medium text-amber-900">
            Draft preview — not indexed · status may be unpublished
          </p>
        </Container>
      </section>
      <article className="site-section bg-white">
        <Container size="narrow">
          <p className="text-xs font-semibold uppercase tracking-wide text-secondary">
            {post.category}
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-primary text-balance">
            {post.title}
          </h1>
          <p className="mt-4 text-lg text-muted leading-relaxed">{post.description}</p>
          <div className="mt-10">
            <MarkdownContent content={post.content} />
          </div>
        </Container>
      </article>
    </CorporateShell>
  );
}
