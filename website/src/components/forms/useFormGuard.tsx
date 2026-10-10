"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Same spam guard as the price calculator: a hidden honeypot field plus the
 * time the form was open. The API drops bot-looking submissions silently.
 */
export function useFormGuard() {
  // Set after mount: reading the clock during render breaks static prerendering.
  const shownAt = useRef<number | null>(null);
  const [honeypot, setHoneypot] = useState("");

  useEffect(() => {
    shownAt.current = Date.now();
  }, []);

  const guardFields = useCallback(
    () => ({
      website: honeypot,
      form_elapsed_ms: shownAt.current == null ? 0 : Math.max(0, Date.now() - shownAt.current),
    }),
    [honeypot]
  );

  const reset = useCallback(() => {
    shownAt.current = Date.now();
    setHoneypot("");
  }, []);

  const field = (
    <div aria-hidden="true" className="absolute -left-[10000px] h-px w-px overflow-hidden">
      <label>
        Website
        <input
          tabIndex={-1}
          autoComplete="off"
          name="website"
          value={honeypot}
          onChange={(e) => setHoneypot(e.target.value)}
        />
      </label>
    </div>
  );

  return { guardFields, honeypotField: field, reset };
}
