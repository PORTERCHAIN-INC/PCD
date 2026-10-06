"use client";

import Link from "next/link";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Button } from "@/components/crm/primitives";
import { blogApi, type BlogAuthor } from "@/lib/blog";
import AdminPage from "@/components/layout/AdminPage";

const EMPTY = { id: "", name: "", role: "", bio: "" };

export default function BlogAuthorsClient() {
  const qc = useQueryClient();
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const { data: authors = [], isLoading } = useQuery({
    queryKey: ["blog-authors"],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => blogApi.listAuthors(await getApiToken()),
  });

  async function handleCreate() {
    setSaving(true);
    setError("");
    try {
      await blogApi.createAuthor(await getApiToken(), {
        id: form.id.trim(),
        name: form.name.trim(),
        role: form.role.trim(),
        bio: form.bio.trim(),
      });
      setForm(EMPTY);
      await qc.invalidateQueries({ queryKey: ["blog-authors"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create author");
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdate(author: BlogAuthor, patch: Partial<BlogAuthor>) {
    setError("");
    try {
      await blogApi.updateAuthor(await getApiToken(), author.id, {
        name: patch.name,
        role: patch.role,
        bio: patch.bio,
      });
      await qc.invalidateQueries({ queryKey: ["blog-authors"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update author");
    }
  }

  async function handleDelete(id: string) {
    if (!confirm(`Delete author “${id}”? Posts must not reference this id.`)) return;
    setError("");
    try {
      await blogApi.removeAuthor(await getApiToken(), id);
      await qc.invalidateQueries({ queryKey: ["blog-authors"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete author");
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <PageSkeleton rows={3} />
      </div>
    );
  }

  return (
    <AdminPage>
      <Link href="/blog" className="inline-flex items-center gap-2 text-sm text-secondary">
        <ArrowLeft className="h-4 w-4" /> Back to blog
      </Link>
      <div>
        <h1 className="text-2xl font-bold text-primary">Blog authors</h1>
        <p className="text-sm text-muted">
          CMS rows for website /authors — ids must match BlogPost.author_id
        </p>
      </div>
      {error ? (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      ) : null}

      <div className="rounded-2xl border border-primary/10 bg-white p-4 space-y-3">
        <p className="text-sm font-semibold text-primary">Add author</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
            placeholder="id (e.g. jane-doe)"
            value={form.id}
            onChange={(e) => setForm((f) => ({ ...f, id: e.target.value }))}
          />
          <input
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
            placeholder="Name"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          />
          <input
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
            placeholder="Role"
            value={form.role}
            onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
          />
          <input
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm sm:col-span-2"
            placeholder="Bio"
            value={form.bio}
            onChange={(e) => setForm((f) => ({ ...f, bio: e.target.value }))}
          />
        </div>
        <Button
          onClick={() => void handleCreate()}
          disabled={saving || !form.id.trim() || !form.name.trim()}
        >
          <Plus className="h-4 w-4" /> {saving ? "Saving…" : "Create author"}
        </Button>
      </div>

      <ul className="space-y-4">
        {authors.map((author) => (
          <li
            key={author.id}
            className="rounded-2xl border border-primary/10 bg-white p-4 space-y-3"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-primary">{author.name}</p>
                <p className="text-xs text-muted font-mono">{author.id}</p>
              </div>
              <Button variant="danger" onClick={() => void handleDelete(author.id)}>
                <Trash2 className="h-4 w-4" /> Delete
              </Button>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
                defaultValue={author.name}
                onBlur={(e) => {
                  if (e.target.value !== author.name) {
                    void handleUpdate(author, { name: e.target.value });
                  }
                }}
              />
              <input
                className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
                defaultValue={author.role}
                onBlur={(e) => {
                  if (e.target.value !== author.role) {
                    void handleUpdate(author, { role: e.target.value });
                  }
                }}
              />
              <textarea
                className="rounded-xl border border-primary/10 px-3 py-2 text-sm sm:col-span-2 min-h-[72px]"
                defaultValue={author.bio}
                onBlur={(e) => {
                  if (e.target.value !== author.bio) {
                    void handleUpdate(author, { bio: e.target.value });
                  }
                }}
              />
            </div>
          </li>
        ))}
      </ul>
    </AdminPage>
  );
}
