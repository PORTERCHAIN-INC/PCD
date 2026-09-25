/**
 * Blog author fallback SSOT — seeded into Postgres `blog_authors` on migrate.
 * Prefer CMS/API rows when available; keep ids in sync with BlogPost.author_id.
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
    name: "Porterchain Team",
    role: "Editorial",
    bio: "Insights from the Porterchain commercial logistics team.",
  },
  "peter-porter": {
    id: "peter-porter",
    name: "Peter Porter",
    role: "Founder & CEO",
    bio: "Building Canada's most trusted commercial logistics partner for local businesses.",
  },
  "sarah-chen": {
    id: "sarah-chen",
    name: "Sarah Chen",
    role: "Head of Dispatch Operations",
    bio: "Operations leader focused on SLA execution, route planning, and partner network quality.",
  },
  "marcus-okonkwo": {
    id: "marcus-okonkwo",
    name: "Marcus Okonkwo",
    role: "Principal Engineer",
    bio: "Engineering lead for routing, tracking systems, and delivery operations reliability.",
  },
};

export function getBlogAuthor(id: string): BlogAuthor {
  return (
    BLOG_AUTHORS[id] ?? {
      id: "porterchain",
      name: "Porterchain Team",
      role: "Editorial",
      bio: "Insights from the Porterchain commercial logistics team.",
    }
  );
}
