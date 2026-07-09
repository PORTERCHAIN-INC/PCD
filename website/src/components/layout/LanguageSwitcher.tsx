"use client";

import { useLocale } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import { Globe, ChevronDown } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { routing, type Locale } from "@/i18n/routing";

const localeLabels: Record<Locale, string> = {
  en: "English",
  fr: "Français",
};

interface LanguageSwitcherProps {
  /** White text for primary / transparent navbar bars */
  lightText?: boolean;
  /** @deprecated Use lightText — inverted legacy prop */
  scrolled?: boolean;
}

export default function LanguageSwitcher({ lightText, scrolled }: LanguageSwitcherProps) {
  const useLightText = lightText ?? !scrolled;
  const locale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const switchLocale = (newLocale: Locale) => {
    router.replace(pathname, { locale: newLocale });
    setOpen(false);
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "flex items-center gap-1.5 px-3 py-2.5 min-h-[2.75rem] type-nav rounded-lg transition-colors cursor-pointer",
          useLightText
            ? "text-white/80 hover:text-white hover:bg-white/10"
            : "text-primary/80 hover:text-primary hover:bg-gray-bg"
        )}
        aria-label="Select language"
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <Globe className="w-4 h-4" />
        <span className="uppercase">{locale}</span>
        <ChevronDown className={cn("w-3.5 h-3.5 transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <ul
          role="listbox"
          className="absolute top-full right-0 mt-1 w-40 rounded-xl bg-white shadow-premium border border-gray-100 py-1 overflow-hidden z-50"
        >
          {routing.locales.map((loc) => (
            <li key={loc} role="option" aria-selected={locale === loc}>
              <button
                onClick={() => switchLocale(loc)}
                className={cn(
                  "w-full text-left px-4 py-3 min-h-[2.75rem] type-nav transition-colors cursor-pointer",
                  locale === loc
                    ? "bg-secondary/10 text-secondary font-bold"
                    : "text-primary/80 hover:bg-gray-bg hover:text-primary font-semibold hover:font-bold"
                )}
              >
                {localeLabels[loc]}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
