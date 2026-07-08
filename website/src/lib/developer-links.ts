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

  return {
    openApiDocs: { id: "openApiDocs", href: `${apiBase}/docs`, external: true },
    openApiJson: { id: "openApiJson", href: `${apiBase}/openapi.json`, external: true },
    partnerGuide: { id: "partnerGuide", href: `${GITHUB_DOCS}/PARTNER_GUIDE.md`, external: true },
    postman: { id: "postman", href: `${GITHUB_DOCS}/porterchain.postman.json`, external: true },
    changelog: { id: "changelog", href: `${GITHUB_DOCS}/CHANGELOG.md`, external: true },
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
