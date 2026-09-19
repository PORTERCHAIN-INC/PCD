"use client";

import { Button } from "@/components/crm/primitives";

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
        <Button variant="outline" disabled={offset <= 0} onClick={() => onPage(prev)}>
          Previous
        </Button>
        <Button variant="outline" disabled={next >= total} onClick={() => onPage(next)}>
          Next
        </Button>
      </div>
    </div>
  );
}
