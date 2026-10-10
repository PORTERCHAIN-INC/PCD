"use client";

import { useState, type ReactNode } from "react";

/** Progressive disclosure for long lists: first `step` rows, then "Show N more". */
export function useShowMore<T>(items: T[], step = 10): { visible: T[]; more: ReactNode } {
  const [limit, setLimit] = useState(step);
  const hidden = items.length - limit;
  return {
    visible: hidden > 0 ? items.slice(0, limit) : items,
    more:
      items.length > step ? (
        <div className="flex justify-center gap-4 py-3 text-sm font-semibold text-secondary">
          {hidden > 0 && (
            <button
              type="button"
              className="hover:underline"
              onClick={() => setLimit((l) => l + step * 3)}
            >
              Show {Math.min(hidden, step * 3)} more of {hidden}
            </button>
          )}
          {limit > step && (
            <button
              type="button"
              className="text-muted hover:underline"
              onClick={() => setLimit(step)}
            >
              Show less
            </button>
          )}
        </div>
      ) : null,
  };
}
