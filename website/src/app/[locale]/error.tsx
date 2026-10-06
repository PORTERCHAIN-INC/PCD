"use client";

import { useEffect } from "react";

export default function LocaleError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto max-w-lg px-4 py-16" role="alert">
      <h1 className="text-xl font-semibold text-primary">This page could not load</h1>
      <p className="mt-2 text-sm text-muted">{error.message || "Try again."}</p>
      <button type="button" onClick={reset} className="btn-secondary mt-6">
        Retry
      </button>
    </div>
  );
}
