import { getPorterchainApiBase } from "@/lib/api-base";
import { publicEnv } from "@/lib/env";

const GITHUB_DOCS = "https://github.com/porterchain/PCD/blob/main/docs/api";
const GITHUB_ARCH = "https://github.com/porterchain/PCD/blob/main/docs/architecture";

export type DeveloperLink = {
  id: string;
  href: string;
  external: boolean;
};

/** Public developer portal links — OpenAPI live, repo docs for guides and collections. */
export function getDeveloperLinks(): Record<string, DeveloperLink> {
  const apiBase = getPorterchainApiBase();
  // The API hides /docs + /openapi.json in production (API_DOCS_ENABLED=false).
  // Unless the public API reference is explicitly re-enabled, send developers to the
  // signed-in merchant API page instead of a 404.
  const liveDocs = process.env.NEXT_PUBLIC_API_DOCS_PUBLIC === "true";
  const signedInApi = `${publicEnv.merchantPortalUrl}/api`;

  return {
    openApiDocs: {
      id: "openApiDocs",
      href: liveDocs ? `${apiBase}/docs` : signedInApi,
      external: true,
    },
    openApiJson: {
      id: "openApiJson",
      href: liveDocs ? `${apiBase}/openapi.json` : signedInApi,
      external: true,
    },
    partnerGuide: {
      id: "partnerGuide",
      href: "/developers/docs/partner-guide",
      external: false,
    },
    postman: { id: "postman", href: `${GITHUB_DOCS}/porterchain.postman.json`, external: true },
    changelog: {
      id: "changelog",
      href: "/developers/docs/changelog",
      external: false,
    },
    merchantFlow: {
      id: "merchantFlow",
      href: `${GITHUB_ARCH}/MERCHANT_FLOW.md`,
      external: true,
    },
    apiKeys: {
      id: "apiKeys",
      href: `${publicEnv.merchantPortalUrl}/api`,
      external: true,
    },
  };
}
