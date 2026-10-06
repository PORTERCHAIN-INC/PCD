import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import BlogAuthorsClient from "@/components/blog/BlogAuthorsClient";
import { adminServerFetch } from "@/lib/server-api";

export default async function BlogAuthorsPage() {
  const client = new QueryClient();
  const authors = await adminServerFetch<unknown>("/v1/admin/blog/authors");
  if (authors) client.setQueryData(["blog-authors"], authors);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <BlogAuthorsClient />
    </HydrationBoundary>
  );
}
