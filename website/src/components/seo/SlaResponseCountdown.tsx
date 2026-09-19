"use client";

import { useEffect, useState } from "react";
import {
  formatQuoteResponseDeadline,
  getNextQuoteResponseDeadline,
} from "@/lib/seo/quote-response-deadline";

type Props = {
  locale?: string;
  label?: string;
  expiredLabel?: string;
};

function formatCountdown(ms: number): string {
  if (ms <= 0) return "0:00:00";
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export default function SlaResponseCountdown({
  locale = "en",
  label = "Quote response by",
  expiredLabel = "Next response window opens soon",
}: Props) {
  const [deadline, setDeadline] = useState<Date | null>(null);
  const [remainingMs, setRemainingMs] = useState(0);

  useEffect(() => {
    const next = getNextQuoteResponseDeadline();
    setDeadline(next);
    setRemainingMs(next.getTime() - Date.now());
    const id = window.setInterval(() => {
      const d = getNextQuoteResponseDeadline();
      setDeadline(d);
      setRemainingMs(d.getTime() - Date.now());
    }, 1000);
    return () => window.clearInterval(id);
  }, []);

  if (!deadline) return null;

  const expired = remainingMs <= 0;

  return (
    <div
      className="rounded-lg border border-primary/10 bg-gray-bg px-4 py-3 text-sm"
      role="status"
      aria-live="polite"
    >
      <p className="font-medium text-primary">
        {label}{" "}
        <time dateTime={deadline.toISOString()}>
          {formatQuoteResponseDeadline(deadline, locale)}
        </time>
      </p>
      <p className="mt-1 text-muted tabular-nums">
        {expired ? expiredLabel : formatCountdown(remainingMs)}
      </p>
    </div>
  );
}
