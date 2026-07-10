"use client";

import { useState, type FormEvent } from "react";
import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";
import { submitInquiry } from "@/lib/submit-inquiry";

const COUNTRY_CODES = [
  { code: "+1", label: "CA +1" },
  { code: "+1", label: "US +1" },
  { code: "+44", label: "UK +44" },
  { code: "+33", label: "FR +33" },
  { code: "+49", label: "DE +49" },
  { code: "+91", label: "IN +91" },
] as const;

interface InquiryFormProps {
  id?: string;
  variant?: "hero" | "inline" | "final";
  className?: string;
}

export default function InquiryForm({
  id = "inquiry",
  variant = "hero",
  className,
}: InquiryFormProps) {
  const t = useTranslations("businessPage.inquiry");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [extension, setExtension] = useState("");
  const [countryCode, setCountryCode] = useState("+1");
  const [agreed, setAgreed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email || !phone || !agreed) return;

    setSubmitting(true);
    setError(null);

    const fullPhone = `${countryCode} ${phone}${extension ? ` ext. ${extension}` : ""}`;

    try {
      await submitInquiry({
        email,
        phone: fullPhone,
        source: "website",
        source_page: "/business",
        form: "business",
        message: `Business inquiry from porterchain.com/business (${variant})`,
      });
    } catch {
      setError(t("errorMessage"));
      setSubmitting(false);
      return;
    }

    track(ANALYTICS_EVENTS.BUSINESS_INQUIRY_SUBMIT, { source_section: variant });
    setSubmitting(false);
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        className={cn("rounded-2xl bg-white p-8 sm:p-10 text-center biz-shadow-lg", className)}
      >
        <div className="w-14 h-14 rounded-full bg-[#ff7a00]/10 flex items-center justify-center mx-auto mb-5">
          <Check className="w-7 h-7 text-[#ff7a00]" />
        </div>
        <h3 className="text-xl font-semibold text-[#091b1c] mb-2">{t("successTitle")}</h3>
        <p className="text-[#5c6b6c] text-sm leading-relaxed">{t("successMessage")}</p>
      </motion.div>
    );
  }

  const isCompact = variant === "inline";

  return (
    <motion.div
      id={id}
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
      className={cn(
        "rounded-2xl bg-white p-6 sm:p-8 biz-shadow-lg border border-[#091b1c]/5",
        variant === "hero" && "lg:p-9",
        variant === "final" && "max-w-xl mx-auto",
        className
      )}
    >
      {!isCompact && (
        <div className="mb-6">
          <h3 className="text-xl sm:text-2xl font-semibold text-[#091b1c] tracking-tight">
            {t("title")}
          </h3>
          <p className="mt-2 text-sm text-[#5c6b6c] leading-relaxed">{t("subtitle")}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div>
          <label
            htmlFor={`${id}-email`}
            className="block text-sm font-medium text-[#091b1c] mb-1.5"
          >
            {t("workEmail")} <span className="text-[#ff7a00]">*</span>
          </label>
          <input
            id={`${id}-email`}
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t("workEmailPlaceholder")}
            className="biz-input"
          />
        </div>

        <div>
          <label
            htmlFor={`${id}-phone`}
            className="block text-sm font-medium text-[#091b1c] mb-1.5"
          >
            {t("phone")} <span className="text-[#ff7a00]">*</span>
          </label>
          <div className="flex gap-2">
            <select
              aria-label={t("countryCode")}
              value={countryCode}
              onChange={(e) => setCountryCode(e.target.value)}
              className="biz-input w-[7.5rem] shrink-0 text-sm"
            >
              {COUNTRY_CODES.map((c) => (
                <option key={c.label} value={c.code}>
                  {c.label}
                </option>
              ))}
            </select>
            <input
              id={`${id}-phone`}
              type="tel"
              required
              autoComplete="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder={t("phonePlaceholder")}
              className="biz-input flex-1"
            />
          </div>
        </div>

        <div>
          <label htmlFor={`${id}-ext`} className="block text-sm font-medium text-[#091b1c] mb-1.5">
            {t("extension")} <span className="text-[#5c6b6c] font-normal">({t("optional")})</span>
          </label>
          <input
            id={`${id}-ext`}
            type="text"
            inputMode="numeric"
            value={extension}
            onChange={(e) => setExtension(e.target.value)}
            placeholder={t("extensionPlaceholder")}
            className="biz-input"
          />
        </div>

        <label className="flex items-start gap-3 cursor-pointer group py-1 min-h-[2.75rem]">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
            className="mt-0.5 w-5 h-5 shrink-0 rounded border-[#091b1c]/20 text-[#ff7a00] focus:ring-[#ff7a00]/30"
            required
          />
          <span className="text-sm text-[#5c6b6c] group-hover:text-[#091b1c] transition-colors leading-relaxed">
            {t("consent")}
          </span>
        </label>

        <button
          type="submit"
          disabled={submitting || !agreed}
          className="w-full flex items-center justify-center gap-2 min-h-[2.75rem] px-6 py-3.5 rounded-xl bg-[#ff7a00] text-white font-semibold text-sm hover:bg-[#e66e00] transition-all disabled:opacity-50 disabled:cursor-not-allowed biz-shadow-glow hover:scale-[1.01] active:scale-[0.99]"
        >
          {submitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              {t("submitting")}
            </>
          ) : (
            t("submit")
          )}
        </button>
        {error && (
          <p className="text-sm text-red-600 text-center" role="alert">
            {error}
          </p>
        )}

        <ul className="flex flex-wrap justify-center gap-x-5 gap-y-1 pt-1">
          {(["noObligation", "noLongForms", "responseTime"] as const).map((key) => (
            <li key={key} className="flex items-center gap-1.5 text-xs text-[#5c6b6c]">
              <Check className="w-3.5 h-3.5 text-[#ff7a00]" />
              {t(`assurances.${key}`)}
            </li>
          ))}
        </ul>
      </form>
    </motion.div>
  );
}
