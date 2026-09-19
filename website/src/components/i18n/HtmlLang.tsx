"use client";

import { useEffect } from "react";

/** Keep <html lang> in sync for locale routes (root layout owns the tag). */
export default function HtmlLang({ locale }: { locale: string }) {
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  return null;
}
