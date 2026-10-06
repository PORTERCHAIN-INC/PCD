import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import BlogEditClient from "@/components/blog/BlogEditClient";
import { adminServerFetch } from "@/lib/server-api";

type Props = { params: Promise<{ id: string }> };

export default async function BlogEditPage({ params }: Props) {
  const { id } = await params;
  const client = new QueryClient();
  const post = await adminServerFetch<unknown>(`/v1/admin/blog/posts/${id}`);
  if (post) client.setQueryData(["blog-post", id], post);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <BlogEditClient params={params} />
    </HydrationBoundary>
  );
}
