export interface BlogAuthor {
  id: string;
  name: string;
  role: string;
  bio: string;
}

export const blogAuthors: Record<string, BlogAuthor> = {
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

export function getAuthor(id: string): BlogAuthor {
  return (
    blogAuthors[id] ?? {
      id: "porterchain",
      name: "Porterchain Team",
      role: "Editorial",
      bio: "Insights from the Porterchain commercial logistics team.",
    }
  );
}
