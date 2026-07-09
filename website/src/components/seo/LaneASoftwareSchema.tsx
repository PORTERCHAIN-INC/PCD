import { JsonLd } from "@/components/seo";
import { buildSoftwareApplicationSchema } from "@/lib/seo/schema";

/** Optional SoftwareApplication schema for legacy Lane A pages (prefer delivery schema on customer paths). */
export default function LaneASoftwareSchema() {
  return <JsonLd data={buildSoftwareApplicationSchema()} />;
}
