"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Button } from "@/components/crm/primitives";
import BlogPostForm from "@/components/blog/BlogPostForm";
import { blogApi, slugifyTitle, type BlogPostInput } from "@/lib/blog";

const EMPTY: BlogPostInput = {
  slug: "",
  locale: "en",
  title: "",
  description: "",
  body_md: "",
  category: "logistics",
  author_id: "porterchain",
  status: "draft",
  featured: false,
  trending: false,
  case_study: false,
  tags: [],
  cover_image_url: null,
  published_at: null,
  scheduled_publish_at: null,
};

export default function NewBlogPostPage() {
  const router = useRouter();
  const { getApiToken } = useAdminAuth();
  const [form, setForm] = useState<BlogPostInput>(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit() {
    setSaving(true);
    setError("");
    try {
      const token = await getApiToken();
      const slug = form.slug.trim() || slugifyTitle(form.title);
      const created = await blogApi.create(token, { ...form, slug });
      router.push(`/blog/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create post");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <Link href="/blog" className="inline-flex items-center gap-2 text-sm text-secondary">
        <ArrowLeft className="h-4 w-4" /> Back to blog
      </Link>
      <div>
        <h1 className="text-2xl font-bold text-primary">New blog post</h1>
        <p className="text-sm text-muted">
          Create EN or FR content — add a matching locale pair for SEO.
        </p>
      </div>
      {error ? (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      ) : null}
      <BlogPostForm value={form} onChange={setForm} getToken={getApiToken} />
      <div className="flex gap-3">
        <Button onClick={() => void handleSubmit()} disabled={saving || !form.title.trim()}>
          {saving ? "Creating…" : "Create post"}
        </Button>
        <Link href="/blog">
          <Button variant="outline">Cancel</Button>
        </Link>
      </div>
    </div>
  );
}
