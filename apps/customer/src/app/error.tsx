"use client";

export default function CustomerError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 px-6 py-8" role="alert">
      <h1 className="text-lg font-semibold text-red-800">This page could not load</h1>
      <p className="mt-1 text-sm text-red-700">{error.message || "Try again."}</p>
      <button
        type="button"
        onClick={reset}
        className="mt-4 rounded-xl border border-red-200 bg-white px-4 py-2 text-sm font-semibold text-red-700"
      >
        Retry
      </button>
    </div>
  );
}
