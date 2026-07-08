"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { Check, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { publicEnv } from "@/lib/env";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";

const INQUIRY_TYPES = ["sales", "support", "partnership", "careers", "api"] as const;
type InquiryType = (typeof INQUIRY_TYPES)[number];

export default function ContactInquiryForm() {
  const t = useTranslations("corporate.contact.form");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [inquiryType, setInquiryType] = useState<InquiryType>("sales");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);

    const form = e.currentTarget;
    const data = new FormData(form);
    const name = String(data.get("name") ?? "");
    const businessName = String(data.get("businessName") ?? "");
    const email = String(data.get("email") ?? "");
    const phone = String(data.get("phone") ?? "");
    const message = String(data.get("message") ?? "");

    const subject = encodeURIComponent(`[${inquiryType}] Porterchain inquiry from ${name}`);
    const body = encodeURIComponent(
      [
        `Name: ${name}`,
        businessName ? `Business: ${businessName}` : null,
        `Email: ${email}`,
        phone ? `Phone: ${phone}` : null,
        `Inquiry type: ${inquiryType}`,
        "",
        message,
      ]
        .filter(Boolean)
        .join("\n")
    );

    window.location.href = `mailto:${publicEnv.contactEmail}?subject=${subject}&body=${body}`;
    track(ANALYTICS_EVENTS.CONTACT_FORM_SUBMIT_SUCCESS, {
      inquiry_type: inquiryType,
      source_section: "contact_page",
    });
    await new Promise((r) => setTimeout(r, 400));
    setLoading(false);
    setSubmitted(true);
  }

  if (submitted) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        className="card-surface p-8 sm:p-10 text-center h-full flex flex-col items-center justify-center min-h-[28rem]"
      >
        <div className="w-14 h-14 rounded-full bg-secondary/10 flex items-center justify-center mb-5">
          <Check className="w-7 h-7 text-secondary" />
        </div>
        <h3 className="text-xl font-semibold text-primary">{t("successTitle")}</h3>
        <p className="mt-2 text-sm text-muted leading-relaxed max-w-sm">{t("successMessage")}</p>
      </motion.div>
    );
  }

  return (
    <div>
      <form onSubmit={handleSubmit} className="card-surface p-6 sm:p-8 space-y-5">
        <div>
          <h2 className="text-xl font-semibold text-primary tracking-tight">{t("title")}</h2>
          <p className="mt-1.5 text-sm text-muted">{t("subtitle")}</p>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <Field label={t("name")} name="name" required autoComplete="name" />
          <Field label={t("businessName")} name="businessName" autoComplete="organization" />
          <Field label={t("email")} name="email" type="email" required autoComplete="email" />
          <Field label={t("phone")} name="phone" type="tel" autoComplete="tel" />
        </div>

        <div>
          <label htmlFor="message" className="block text-sm font-medium text-primary mb-1.5">
            {t("message")}
          </label>
          <textarea
            id="message"
            name="message"
            rows={4}
            required
            className="w-full rounded-xl border border-primary/10 px-4 py-3 text-sm text-primary outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/15 resize-none transition-shadow"
          />
        </div>

        <fieldset>
          <legend className="block text-sm font-medium text-primary mb-2.5">
            {t("inquiryType")}
          </legend>
          <div className="flex flex-wrap gap-2">
            {INQUIRY_TYPES.map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setInquiryType(type)}
                className={cn(
                  "px-3.5 py-2 rounded-full text-xs font-semibold transition-all cursor-pointer min-h-[2.25rem]",
                  inquiryType === type
                    ? "bg-secondary text-white shadow-md shadow-secondary/20"
                    : "bg-gray-bg text-primary/70 border border-primary/[0.08] hover:border-secondary/30 hover:text-primary"
                )}
                aria-pressed={inquiryType === type}
              >
                {t(`inquiryTypes.${type}`)}
              </button>
            ))}
          </div>
          <input type="hidden" name="inquiryType" value={inquiryType} />
        </fieldset>

        <button
          type="submit"
          disabled={loading}
          className={cn(
            "w-full py-3.5 rounded-full bg-secondary text-white font-semibold text-sm",
            "hover:bg-[#1d4ed8] transition-all hover:shadow-lg hover:shadow-secondary/25",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          {loading ? t("sending") : t("submit")}
        </button>
      </form>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="mt-4 flex items-center justify-center gap-3 rounded-xl bg-secondary/5 border border-secondary/10 px-4 py-3"
      >
        <Clock className="w-4 h-4 text-secondary shrink-0" aria-hidden />
        <p className="text-sm text-primary">
          <span className="text-muted">{t("responseLabel")}</span>{" "}
          <span className="font-semibold text-secondary">{t("responseTime")}</span>
        </p>
      </motion.div>
    </div>
  );
}

function Field({
  label,
  name,
  type = "text",
  required,
  autoComplete,
}: {
  label: string;
  name: string;
  type?: string;
  required?: boolean;
  autoComplete?: string;
}) {
  return (
    <div>
      <label htmlFor={name} className="block text-sm font-medium text-primary mb-1.5">
        {label}
        {required && <span className="text-secondary ml-0.5">*</span>}
      </label>
      <input
        id={name}
        name={name}
        type={type}
        required={required}
        autoComplete={autoComplete}
        className="w-full rounded-xl border border-primary/10 px-4 py-2.5 text-sm text-primary outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/15 min-h-[2.75rem] transition-shadow bg-white"
      />
    </div>
  );
}
