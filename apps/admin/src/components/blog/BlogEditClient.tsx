"use client";

import Link from "next/link";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useRouter } from "next/navigation";
import { use, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Trash2 } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Button } from "@/components/crm/primitives";
import BlogPostForm from "@/components/blog/BlogPostForm";
import { blogApi, type BlogPostInput } from "@/lib/blog";
import AdminPage from "@/components/layout/AdminPage";

function toInput(post: Awaited<ReturnType<typeof blogApi.detail>>): BlogPostInput {
  return {
    slug: post.slug,
    locale: post.locale,
    title: post.title,
    description: post.description,
    body_md: post.body_md,
    category: post.category,
    author_id: post.author_id,
    status: post.status,
    featured: post.featured,
    trending: post.trending,
    case_study: post.case_study,
    on_time_percent: post.on_time_percent,
    cost_delta_percent: post.cost_delta_percent,
    volume_metric: post.volume_metric,
    tags: post.tags,
    cover_image_url: post.cover_image_url ?? null,
    published_at: post.published_at,
    scheduled_publish_at: post.scheduled_publish_at ?? null,
  };
}

export default function BlogEditClient({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const qc = useQueryClient();
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const [form, setForm] = useState<BlogPostInput | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  const { data: post, isLoading } = useQuery({
    queryKey: ["blog-post", id],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => {
      const row = await blogApi.detail(await getApiToken(), id);
      setForm(toInput(row));
      return row;
    },
  });

  async function handleSave() {
    if (!form) return;
    setSaving(true);
    setError("");
    try {
      const token = await getApiToken();
      await blogApi.update(token, id, form);
      await qc.invalidateQueries({ queryKey: ["blog-post", id] });
      await qc.invalidateQueries({ queryKey: ["blog-posts"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save post");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this blog post permanently?")) return;
    setDeleting(true);
    setError("");
    try {
      const token = await getApiToken();
      await blogApi.remove(token, id);
      await qc.invalidateQueries({ queryKey: ["blog-posts"] });
      router.push("/blog");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete post");
      setDeleting(false);
    }
  }

  if (isLoading || !form) {
    return (
      <div className="flex justify-center py-16">
        <PageSkeleton rows={3} />
      </div>
    );
  }

  if (!post) {
    return (
      <div className="space-y-4">
        <Link href="/blog" className="inline-flex items-center gap-2 text-sm text-secondary">
          <ArrowLeft className="h-4 w-4" /> Back to blog
        </Link>
        <p className="text-muted">Post not found.</p>
      </div>
    );
  }

  return (
    <AdminPage>
      <Link href="/blog" className="inline-flex items-center gap-2 text-sm text-secondary">
        <ArrowLeft className="h-4 w-4" /> Back to blog
      </Link>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Edit blog post</h1>
          <p className="text-sm text-muted">
            /{post.locale}/blog/{post.slug}
          </p>
        </div>
        <Button variant="danger" onClick={() => void handleDelete()} disabled={deleting}>
          <Trash2 className="h-4 w-4" /> {deleting ? "Deleting…" : "Delete"}
        </Button>
      </div>
      {error ? (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      ) : null}
      <BlogPostForm value={form} onChange={setForm} getToken={getApiToken} postId={post.id} />
      <div className="flex gap-3">
        <Button onClick={() => void handleSave()} disabled={saving || !form.title.trim()}>
          {saving ? "Saving…" : "Save changes"}
        </Button>
      </div>
    </AdminPage>
  );
}
