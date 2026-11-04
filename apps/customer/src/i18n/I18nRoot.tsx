"use client";

import { Fragment, useLayoutEffect, useState, type ReactNode } from "react";
import { readLocaleCookie, setLocale, type Locale } from "./core";

/**
 * Server render and hydration are English (no mismatch). Right after hydration, before paint, a
 * French choice remounts the tree so every client component renders through the translating
 * JSX runtime. The inline head script hides the page until then (3 s safety timeout).
 */
export function I18nRoot({ children }: { children: ReactNode }) {
  const [locale, setL] = useState<Locale>("en");
  useLayoutEffect(() => {
    const l = readLocaleCookie(document.cookie);
    if (l !== "en") {
      setLocale(l);
      setL(l);
    }
    document.documentElement.lang = l === "fr" ? "fr-CA" : "en";
    document.documentElement.removeAttribute("data-i18n-pending");
  }, []);
  return <Fragment key={locale}>{children}</Fragment>;
}

/** <head> script: hide body while a French page is being localized. */
export const I18N_HEAD_SCRIPT = `(function(){try{if(/(?:^|;\\s*)pc_locale=fr/.test(document.cookie)){var d=document.documentElement;d.setAttribute("data-i18n-pending","");setTimeout(function(){d.removeAttribute("data-i18n-pending")},3000)}}catch(e){}})();`;
