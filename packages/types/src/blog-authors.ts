/**
 * Blog author fallback SSOT — seeded into Postgres `blog_authors` on migrate.
 * Prefer CMS/API rows when available; keep ids in sync with BlogPost.author_id.
 * Only real authors: the PorterChain team (fictional personas removed Oct 2026).
 */
export type BlogAuthor = {
  id: string;
  name: string;
  role: string;
  bio: string;
};

export const BLOG_AUTHORS: Record<string, BlogAuthor> = {
  porterchain: {
    id: "porterchain",
    name: "PorterChain team",
    role: "Editorial",
    bio: "Practical guides from the PorterChain team in the GTA.",
  },
};

export function getBlogAuthor(id: string): BlogAuthor {
  return (
    BLOG_AUTHORS[id] ?? {
      id: "porterchain",
      name: "PorterChain team",
      role: "Editorial",
      bio: "Practical guides from the PorterChain team in the GTA.",
    }
  );
}
