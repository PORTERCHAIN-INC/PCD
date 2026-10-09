/**
 * Suspense boundary for blog articles rendered on demand (new CMS posts and unknown slugs).
 * Without it, cacheComponents bails out of on-demand static generation on the API fetch and
 * the route answers 500. Prerendered posts are unaffected (their HTML is complete at build).
 * Intentionally empty: no skeleton flash (the site-wide loading screen was removed).
 */
export default function BlogArticleLoading() {
  return <div className="min-h-[60vh]" aria-hidden />;
}
