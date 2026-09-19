"use client";

type Props = {
  total: number;
  limit: number;
  offset: number;
  onPage: (offset: number) => void;
  note?: string;
};

export function ListPager({ total, limit, offset, onPage, note }: Props) {
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);
  const prev = Math.max(0, offset - limit);
  const next = offset + limit;
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm">
      <div>
        <p className="text-muted">
          Showing {from}–{to} of {total}
        </p>
        {note ? <p className="mt-0.5 text-xs text-muted">{note}</p> : null}
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={offset <= 0}
          onClick={() => onPage(prev)}
          className="rounded-xl border border-primary/15 bg-white px-3 py-1.5 text-sm font-medium text-primary disabled:cursor-not-allowed disabled:opacity-50"
        >
          Previous
        </button>
        <button
          type="button"
          disabled={next >= total}
          onClick={() => onPage(next)}
          className="rounded-xl border border-primary/15 bg-white px-3 py-1.5 text-sm font-medium text-primary disabled:cursor-not-allowed disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
