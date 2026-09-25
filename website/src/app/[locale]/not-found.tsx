import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";

export default async function NotFound() {
  const t = await getTranslations("common.notFound");
  const tCta = await getTranslations("common.cta");

  return (
    <SiteShell>
      <section className="site-section bg-white">
        <Container className="max-w-xl text-center">
          <h1 className="text-4xl font-bold text-primary">{t("title")}</h1>
          <p className="mt-4 text-muted">{t("body")}</p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link href="/" className="btn-primary">
              {t("home")}
            </Link>
            <Link href="/sign-up?intent=quote&from=business" className="btn-secondary">
              {tCta("quote")}
            </Link>
          </div>
        </Container>
      </section>
    </SiteShell>
  );
}
