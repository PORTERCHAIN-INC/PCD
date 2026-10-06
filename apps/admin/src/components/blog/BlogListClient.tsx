"use client";

import Link from "next/link";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, RefreshCw } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Badge, Button } from "@/components/crm/primitives";
import AdminPage from "@/components/layout/AdminPage";
import {
  BLOG_CATEGORIES,
  BLOG_LOCALES,
  BLOG_STATUSES,
  blogApi,
  STATUS_TONES,
  type BlogFilters,
} from "@/lib/blog";

function formatWhen(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export default function BlogListClient() {
  const router = useRouter();
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const [filters, setFilters] = useState<BlogFilters>({});

  const {
    data: rows = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["blog-posts", JSON.stringify(filters)],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => blogApi.list(await getApiToken(), filters),
  });

  return (
    <AdminPage>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Blog</h1>
          <p className="text-sm text-muted">
            Manage website blog posts — published posts appear on porterchain.com/blog
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void refetch()}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
          <Link href="/blog/authors">
            <Button variant="outline">Authors</Button>
          </Link>
          <Button onClick={() => router.push("/blog/new")}>
            <Plus className="h-4 w-4" /> New post
          </Button>
        </div>
      </div>

      <div className="rounded-2xl border border-primary/10 bg-white p-4">
        <div className="mb-4 flex flex-wrap gap-2">
          <input
            type="search"
            placeholder="Search title, slug, description…"
            value={filters.search ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value || undefined }))}
            className="min-w-[220px] flex-1 rounded-xl border border-primary/10 px-3 py-2 text-sm"
          />
          <select
            value={filters.locale ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, locale: e.target.value || undefined }))}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All locales</option>
            {BLOG_LOCALES.map((l) => (
              <option key={l} value={l}>
                {l.toUpperCase()}
              </option>
            ))}
          </select>
          <select
            value={filters.status ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value || undefined }))}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            {BLOG_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            value={filters.category ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value || undefined }))}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All categories</option>
            {BLOG_CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <PageSkeleton rows={3} />
          </div>
        ) : rows.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted">No blog posts match these filters.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-primary/10 text-xs uppercase tracking-wide text-muted">
                  <th className="px-3 py-2 font-medium">Title</th>
                  <th className="px-3 py-2 font-medium">Locale</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Category</th>
                  <th className="px-3 py-2 font-medium">Updated</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="border-b border-primary/5 hover:bg-gray-bg/60">
                    <td className="px-3 py-3">
                      <Link
                        href={`/blog/${row.id}`}
                        className="font-medium text-primary hover:text-secondary"
                      >
                        {row.title}
                      </Link>
                      <p className="text-xs text-muted">{row.slug}</p>
                    </td>
                    <td className="px-3 py-3 uppercase">{row.locale}</td>
                    <td className="px-3 py-3">
                      <Badge tone={STATUS_TONES[row.status] ?? "slate"}>{row.status}</Badge>
                    </td>
                    <td className={cn("px-3 py-3 capitalize")}>
                      {row.category.replace(/-/g, " ")}
                    </td>
                    <td className="px-3 py-3 text-muted">{formatWhen(row.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AdminPage>
  );
}
