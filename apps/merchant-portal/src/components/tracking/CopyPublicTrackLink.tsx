"use client";

import { copyPublicTrackUrl } from "@/lib/tracking";
import { useState } from "react";

type Props = {
  trackingNumber: string;
  publicUrl?: string | null;
  isSandbox?: boolean;
  className?: string;
};

export function CopyPublicTrackLink({
  trackingNumber,
  publicUrl,
  isSandbox = false,
  className,
}: Props) {
  const [copied, setCopied] = useState(false);

  if (!trackingNumber || isSandbox) return null;

  return (
    <button
      type="button"
      className={
        className ?? "rounded-xl border border-primary/15 px-3 py-1.5 text-xs hover:bg-gray-bg"
      }
      onClick={() => {
        void (async () => {
          const ok = await copyPublicTrackUrl(trackingNumber, publicUrl);
          if (!ok) return;
          setCopied(true);
          window.setTimeout(() => setCopied(false), 2000);
        })();
      }}
    >
      {copied ? "Copied" : "Copy public link"}
    </button>
  );
}
