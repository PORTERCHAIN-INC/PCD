import { getTranslations } from "next-intl/server";
import { RelatedResourcesSection } from "@/components/corporate/sections/CardGridSection";
import { collectResourceItems } from "@/lib/corporate-content";

export default async function TrustDocumentsSection() {
  const t = await getTranslations("corporate.trust.documents");

  return (
    <RelatedResourcesSection
      label={t("label")}
      title={t("title")}
      items={collectResourceItems(t, "items", 5)}
      className="bg-white border-t border-primary/[0.06]"
    />
  );
}
