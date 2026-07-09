import fs from "node:fs";
import path from "node:path";

export const DEVELOPER_DOC_SLUGS = ["partner-guide", "changelog"] as const;

export type DeveloperDocSlug = (typeof DEVELOPER_DOC_SLUGS)[number];

const DOC_FILES: Record<DeveloperDocSlug, string> = {
  "partner-guide": "PARTNER_GUIDE.md",
  changelog: "CHANGELOG.md",
};

function apiDocsDir(): string {
  return path.join(process.cwd(), "..", "docs", "api");
}

export function isValidDeveloperDocSlug(slug: string): slug is DeveloperDocSlug {
  return DEVELOPER_DOC_SLUGS.includes(slug as DeveloperDocSlug);
}

export type DeveloperDoc = {
  slug: DeveloperDocSlug;
  title: string;
  description: string;
  content: string;
  githubHref: string;
};

const DOC_META: Record<DeveloperDocSlug, { title: string; description: string }> = {
  "partner-guide": {
    title: "Partner API guide",
    description:
      "Authentication, API v1 scopes, quote-to-delivery flows, webhooks, and production readiness.",
  },
  changelog: {
    title: "API changelog",
    description: "Versioning policy, breaking-change notice windows, and release history.",
  },
};

const GITHUB_DOCS_BASE = "https://github.com/porterchain/PCD/blob/main/docs/api";

export function getDeveloperDoc(slug: DeveloperDocSlug): DeveloperDoc | null {
  const fileName = DOC_FILES[slug];
  const filePath = path.join(apiDocsDir(), fileName);
  if (!fs.existsSync(filePath)) return null;

  const content = fs.readFileSync(filePath, "utf8");
  const meta = DOC_META[slug];

  return {
    slug,
    title: meta.title,
    description: meta.description,
    content,
    githubHref: `${GITHUB_DOCS_BASE}/${fileName}`,
  };
}

export function listDeveloperDocs(): Omit<DeveloperDoc, "content">[] {
  return DEVELOPER_DOC_SLUGS.flatMap((slug) => {
    const doc = getDeveloperDoc(slug);
    if (!doc) return [];
    const { content: _, ...meta } = doc;
    return [meta];
  });
}
