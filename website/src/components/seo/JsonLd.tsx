/**
 * Renders JSON-LD structured data for SEO. No UI; script only.
 * Use for Organization, LocalBusiness, Service, FAQPage, etc.
 * Filters out null/undefined and ensures each item has @context to avoid runtime errors.
 * Escapes < in output per Next.js recommendation for security and parsing.
 */

type JsonLdData = unknown | unknown[] | null | undefined;

export type JsonLdProps = {
  /** Single schema object or array of schema objects. Null/undefined items are filtered out. */
  data: JsonLdData;
};

function isJsonLdObject(value: unknown): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    "@context" in value &&
    typeof (value as Record<string, unknown>)["@context"] === "string"
  );
}

export function JsonLd({ data }: JsonLdProps) {
  const raw = Array.isArray(data) ? data : data != null ? [data] : [];
  const payload = raw.filter(isJsonLdObject);
  if (payload.length === 0) return null;
  const scriptContent = JSON.stringify(payload.length === 1 ? payload[0] : payload).replace(
    /</g,
    "\\u003c"
  );
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: scriptContent }} />;
}
