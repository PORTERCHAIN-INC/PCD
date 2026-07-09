import { JsonLd } from "@/components/seo";
import { buildLocalBusinessSchema, buildOrganizationSchema } from "@/lib/seo/schema";

/** Homepage schema for Phase 1: transportation capacity, not a software SKU. */
export default function HomeDeliverySchema() {
  return <JsonLd data={[buildOrganizationSchema(), buildLocalBusinessSchema()]} />;
}
