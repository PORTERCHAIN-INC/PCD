"use client";

import { useRef, useState } from "react";
import { ImagePlus, Loader2, Trash2 } from "lucide-react";
import { publicEnv } from "@/lib/env";
import { DateField } from "@porterchain/ui/date-fields";
import {
  BLOG_CATEGORIES,
  BLOG_LOCALES,
  BLOG_STATUSES,
  blogApi,
  type BlogPostInput,
} from "@/lib/blog";

type Props = {
  value: BlogPostInput;
  onChange: (next: BlogPostInput) => void;
  getToken: () => Promise<string>;
};

function fieldClassName() {
  return "w-full rounded-xl border border-primary/10 px-3 py-2 text-sm";
}

function absoluteMediaUrl(url: string): string {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  const base = publicEnv.porterchainApiUrl.replace(/\/$/, "");
  return `${base}${url.startsWith("/") ? url : `/${url}`}`;
}

export default function BlogPostForm({ value, onChange, getToken }: Props) {
  const coverInputRef = useRef<HTMLInputElement>(null);
  const bodyInputRef = useRef<HTMLInputElement>(null);
  const bodyRef = useRef<HTMLTextAreaElement>(null);
  const [uploadingCover, setUploadingCover] = useState(false);
  const [uploadingBody, setUploadingBody] = useState(false);
  const [uploadError, setUploadError] = useState("");

  function patch(partial: Partial<BlogPostInput>) {
    onChange({ ...value, ...partial });
  }

  const tagsText = value.tags.join(", ");
  const coverPreview = value.cover_image_url ? absoluteMediaUrl(value.cover_image_url) : "";

  async function uploadFile(file: File): Promise<string> {
    const token = await getToken();
    const { url } = await blogApi.uploadMedia(token, file);
    return url;
  }

  async function handleCoverFile(file: File | null) {
    if (!file) return;
    setUploadingCover(true);
    setUploadError("");
    try {
      const url = await uploadFile(file);
      patch({ cover_image_url: url });
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Cover upload failed");
    } finally {
      setUploadingCover(false);
      if (coverInputRef.current) coverInputRef.current.value = "";
    }
  }

  async function handleBodyFile(file: File | null) {
    if (!file) return;
    setUploadingBody(true);
    setUploadError("");
    try {
      const url = await uploadFile(file);
      const abs = absoluteMediaUrl(url);
      const alt = file.name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ");
      const snippet = `\n\n![${alt}](${abs})\n\n`;
      const el = bodyRef.current;
      if (el) {
        const start = el.selectionStart ?? value.body_md.length;
        const end = el.selectionEnd ?? start;
        const next = value.body_md.slice(0, start) + snippet + value.body_md.slice(end);
        patch({ body_md: next });
        requestAnimationFrame(() => {
          el.focus();
          const pos = start + snippet.length;
          el.setSelectionRange(pos, pos);
        });
      } else {
        patch({ body_md: `${value.body_md}${snippet}` });
      }
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Image upload failed");
    } finally {
      setUploadingBody(false);
      if (bodyInputRef.current) bodyInputRef.current.value = "";
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-primary/10 bg-[#F4F6FA] p-4 text-sm">
        <p className="font-semibold text-primary">Publish checklist</p>
        <ul className="mt-2 space-y-1 text-muted">
          <li className={value.title.trim() ? "text-secondary" : ""}>
            {value.title.trim() ? "✓" : "○"} Title (≤60 chars for SEO)
            {value.title.trim() ? ` · ${value.title.trim().length}` : ""}
          </li>
          <li className={value.description.trim().length >= 40 ? "text-secondary" : ""}>
            {value.description.trim().length >= 40 ? "✓" : "○"} Meta description (≥40 chars)
          </li>
          <li className={value.cover_image_url ? "text-secondary" : ""}>
            {value.cover_image_url ? "✓" : "○"} Cover image
          </li>
          <li className={value.category ? "text-secondary" : ""}>
            {value.category ? "✓" : "○"} Category / niche
          </li>
          <li className={value.body_md.trim().length > 200 ? "text-secondary" : ""}>
            {value.body_md.trim().length > 200 ? "✓" : "○"} Body content
          </li>
          <li className={value.status === "published" ? "text-secondary" : ""}>
            Status: {value.status}
            {value.status === "published" ? " · will revalidate website" : " · draft stays private"}
          </li>
        </ul>
      </div>

      <div className="grid gap-6 rounded-2xl border border-primary/10 bg-white p-6 lg:grid-cols-2">
        <div className="space-y-4">
          <label className="block space-y-1 text-sm">
            <span className="font-medium text-primary">Title</span>
            <input
              className={fieldClassName()}
              value={value.title}
              onChange={(e) => patch({ title: e.target.value })}
              required
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-medium text-primary">Slug</span>
            <input
              className={fieldClassName()}
              value={value.slug}
              onChange={(e) => patch({ slug: e.target.value })}
              placeholder="auto-from-title-if-empty"
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-medium text-primary">Description</span>
            <textarea
              className={`${fieldClassName()} min-h-[88px]`}
              value={value.description}
              onChange={(e) => patch({ description: e.target.value })}
            />
          </label>

          <div className="space-y-2 rounded-xl border border-primary/10 bg-gray-bg/40 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm font-medium text-primary">Cover image</span>
              <div className="flex flex-wrap gap-2">
                <input
                  ref={coverInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  className="hidden"
                  onChange={(e) => void handleCoverFile(e.target.files?.[0] ?? null)}
                />
                <button
                  type="button"
                  disabled={uploadingCover}
                  onClick={() => coverInputRef.current?.click()}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-primary/10 bg-white px-3 py-1.5 text-xs font-medium text-primary hover:bg-white disabled:opacity-60"
                >
                  {uploadingCover ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <ImagePlus className="h-3.5 w-3.5" />
                  )}
                  Upload cover
                </button>
                {value.cover_image_url ? (
                  <button
                    type="button"
                    onClick={() => patch({ cover_image_url: null })}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-primary/10 bg-white px-3 py-1.5 text-xs font-medium text-muted hover:text-primary"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Remove
                  </button>
                ) : null}
              </div>
            </div>
            {coverPreview ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={coverPreview}
                alt="Cover preview"
                className="mt-2 h-40 w-full rounded-lg object-cover"
              />
            ) : (
              <p className="text-xs text-muted">
                Optional hero image for the article card and post page. JPG, PNG, WebP, or GIF up to
                5&nbsp;MB.
              </p>
            )}
            <label className="block space-y-1 text-sm">
              <span className="font-medium text-primary">Cover image URL</span>
              <input
                className={fieldClassName()}
                value={value.cover_image_url ?? ""}
                onChange={(e) => patch({ cover_image_url: e.target.value || null })}
                placeholder="/v1/public/blog/media/… or https://…"
              />
            </label>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <label className="block space-y-1 text-sm">
              <span className="font-medium text-primary">Locale</span>
              <select
                className={fieldClassName()}
                value={value.locale}
                onChange={(e) => patch({ locale: e.target.value })}
              >
                {BLOG_LOCALES.map((l) => (
                  <option key={l} value={l}>
                    {l.toUpperCase()}
                  </option>
                ))}
              </select>
            </label>
            <label className="block space-y-1 text-sm">
              <span className="font-medium text-primary">Status</span>
              <select
                className={fieldClassName()}
                value={value.status}
                onChange={(e) => patch({ status: e.target.value })}
              >
                {BLOG_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <label className="block space-y-1 text-sm">
              <span className="font-medium text-primary">Category</span>
              <select
                className={fieldClassName()}
                value={value.category}
                onChange={(e) => patch({ category: e.target.value })}
              >
                {BLOG_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
            <label className="block space-y-1 text-sm">
              <span className="font-medium text-primary">Author ID</span>
              <input
                className={fieldClassName()}
                value={value.author_id}
                onChange={(e) => patch({ author_id: e.target.value })}
              />
            </label>
          </div>
          <label className="block space-y-1 text-sm">
            <span className="font-medium text-primary">Tags (comma-separated)</span>
            <input
              className={fieldClassName()}
              value={tagsText}
              onChange={(e) =>
                patch({
                  tags: e.target.value
                    .split(",")
                    .map((t) => t.trim())
                    .filter(Boolean),
                })
              }
            />
          </label>
          <DateField
            label="Published date"
            value={value.published_at ?? ""}
            onChange={(published) => patch({ published_at: published || null })}
            datePlaceholder="Publish date"
          />
          <div className="flex flex-wrap gap-4 text-sm">
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={value.featured}
                onChange={(e) => patch({ featured: e.target.checked })}
              />
              Featured
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={value.trending}
                onChange={(e) => patch({ trending: e.target.checked })}
              />
              Trending
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={value.case_study}
                onChange={(e) => patch({ case_study: e.target.checked })}
              />
              Case study
            </label>
          </div>
          {value.case_study ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <label className="block space-y-1 text-sm">
                <span className="font-medium text-primary">On-time %</span>
                <input
                  className={fieldClassName()}
                  value={value.on_time_percent ?? ""}
                  onChange={(e) => patch({ on_time_percent: e.target.value || null })}
                />
              </label>
              <label className="block space-y-1 text-sm">
                <span className="font-medium text-primary">Cost delta %</span>
                <input
                  className={fieldClassName()}
                  value={value.cost_delta_percent ?? ""}
                  onChange={(e) => patch({ cost_delta_percent: e.target.value || null })}
                />
              </label>
              <label className="block space-y-1 text-sm">
                <span className="font-medium text-primary">Volume metric</span>
                <input
                  className={fieldClassName()}
                  value={value.volume_metric ?? ""}
                  onChange={(e) => patch({ volume_metric: e.target.value || null })}
                />
              </label>
            </div>
          ) : null}
          {uploadError ? <p className="text-sm text-red-600">{uploadError}</p> : null}
        </div>

        <div className="space-y-2 lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-sm font-medium text-primary">Body (Markdown)</span>
            <div>
              <input
                ref={bodyInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif"
                className="hidden"
                onChange={(e) => void handleBodyFile(e.target.files?.[0] ?? null)}
              />
              <button
                type="button"
                disabled={uploadingBody}
                onClick={() => bodyInputRef.current?.click()}
                className="inline-flex items-center gap-1.5 rounded-lg border border-primary/10 bg-white px-3 py-1.5 text-xs font-medium text-primary hover:bg-gray-bg disabled:opacity-60"
              >
                {uploadingBody ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <ImagePlus className="h-3.5 w-3.5" />
                )}
                Insert image in body
              </button>
            </div>
          </div>
          <textarea
            ref={bodyRef}
            className={`${fieldClassName()} min-h-[280px] font-mono text-[13px] leading-relaxed`}
            value={value.body_md}
            onChange={(e) => patch({ body_md: e.target.value })}
          />
          <div className="rounded-xl border border-primary/10 bg-[#FAFBFC] p-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Preview</p>
            <pre className="max-h-[280px] overflow-auto whitespace-pre-wrap font-sans text-sm leading-relaxed text-primary">
              {value.body_md.trim() || "Body preview appears here…"}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
