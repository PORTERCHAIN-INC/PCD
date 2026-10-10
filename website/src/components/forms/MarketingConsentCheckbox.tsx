"use client";

import { useLocale } from "next-intl";
import { caslText } from "@/lib/marketing/casl";

type Props = {
  checked: boolean;
  onChange: (checked: boolean) => void;
  /** "dark" for forms on navy backgrounds (footer). */
  tone?: "light" | "dark";
  /** Newsletter forms: the box is the request itself, so it is required. */
  required?: boolean;
  id?: string;
};

/**
 * CASL express consent — separate from the cookie banner, unchecked by default,
 * never pre-ticked. The API stores its own copy of this text + version, IP and time.
 */
export default function MarketingConsentCheckbox({
  checked,
  onChange,
  tone = "light",
  required = false,
  id = "marketing-consent",
}: Props) {
  const locale = useLocale();
  const optional = locale.startsWith("fr") ? "(Facultatif)" : "(Optional)";
  return (
    <label
      htmlFor={id}
      className={`flex items-start gap-3 text-sm ${tone === "dark" ? "text-white/80" : "text-primary"}`}
    >
      <input
        id={id}
        type="checkbox"
        name="marketing_consent"
        className="mt-1 h-4 w-4 shrink-0"
        checked={checked}
        required={required}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span>
        {caslText(locale)}{" "}
        {required ? null : (
          <span className={tone === "dark" ? "text-white/50" : "text-muted"}>{optional}</span>
        )}
      </span>
    </label>
  );
}
