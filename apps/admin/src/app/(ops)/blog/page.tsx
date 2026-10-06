import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import BlogListClient from "@/components/blog/BlogListClient";
import { adminServerFetch } from "@/lib/server-api";

export default async function BlogPage() {
  const client = new QueryClient();
  const posts = await adminServerFetch<unknown>("/v1/admin/blog/posts?limit=500");
  if (posts) client.setQueryData(["blog-posts", "{}"], posts);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <BlogListClient />
    </HydrationBoundary>
  );
}
