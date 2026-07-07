"use client";

import { isGoogleMapsConfigured } from "@/lib/env";
import { useEffect, useState, type ReactNode } from "react";

declare global {
  interface Window {
    gm_authFailure?: () => void;
  }
}

export function MapShell({ children, height }: { children: ReactNode; height: string }) {
  const [authFailed, setAuthFailed] = useState(false);

  useEffect(() => {
    window.gm_authFailure = () => setAuthFailed(true);
    return () => {
      delete window.gm_authFailure;
    };
  }, []);

  if (!isGoogleMapsConfigured()) {
    return (
      <div
        className="flex items-center justify-center rounded-2xl border border-dashed border-primary/20 bg-gray-bg px-4 text-center text-sm text-muted"
        style={{ height }}
      >
        Set <code className="mx-1 rounded bg-white px-1">NEXT_PUBLIC_GOOGLE_MAPS_API_KEY</code> to
        enable the tracking map.
      </div>
    );
  }

  if (authFailed) {
    return (
      <div
        className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-amber-200 bg-amber-50 px-4 text-center text-sm text-amber-950"
        style={{ height }}
      >
        <p className="font-medium">Google Maps is blocked for this site</p>
        <p className="max-w-md text-xs text-amber-900/90">
          In Google Cloud Console, open your Maps JavaScript API key and add{" "}
          <code className="rounded bg-white/80 px-1">http://localhost:3001/*</code> under HTTP
          referrer restrictions, then restart the merchant portal.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
