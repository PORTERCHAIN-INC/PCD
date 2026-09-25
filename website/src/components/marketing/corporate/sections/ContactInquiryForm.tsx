"use client";

import { useState, type FormEvent } from "react";
import { Check, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";
import { getStoredAttribution } from "@/lib/seo/attribution";
import { submitInquiry } from "@/lib/submit-inquiry";

const INQUIRY_TYPES = ["sales", "support", "partnership", "careers", "api"] as const;

const inputClass =
  "w-full rounded-xl border border-primary/10 bg-white px-4 py-3 text-sm text-primary outline-none transition-shadow focus:border-secondary focus:ring-2 focus:ring-secondary/15";

export default function ContactInquiryForm() {
  const t = useTranslations("corporate.contact.form");
  const [name, setName] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [inquiryType, setInquiryType] = useState<(typeof INQUIRY_TYPES)[number]>("sales");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim() || !message.trim()) return;

    setSubmitting(true);
    setError(null);
    const stored = getStoredAttribution();

    try {
      await submitInquiry({
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim() || undefined,
        business_name: businessName.trim() || undefined,
        message: message.trim(),
        inquiry_type: inquiryType,
        source: "website",
        source_page: "/contact",
        form: "contact",
        utm_source: stored.utm_source,
        utm_campaign: stored.utm_campaign,
        utm_medium: stored.utm_medium,
      });
      track(ANALYTICS_EVENTS.CONTACT_FORM_SUBMIT_SUCCESS, {
        source_section: "contact_form",
        inquiry_type: inquiryType,
      });
      if (inquiryType === "sales") {
        track(ANALYTICS_EVENTS.QUOTE_REQUEST, {
          source_section: "contact_form",
          path: "sales_inquiry",
        });
      }
      setSubmitted(true);
    } catch {
      track(ANALYTICS_EVENTS.CONTACT_FORM_SUBMIT_ERROR, {
        source_section: "contact_form",
        inquiry_type: inquiryType,
      });
      setError(t("errorMessage"));
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="rounded-3xl border border-primary/8 bg-[#F4F6FA] p-6 sm:p-8 text-center">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-secondary/10">
          <Check className="h-7 w-7 text-secondary" />
        </div>
        <h2 className="text-xl font-semibold text-primary">{t("successTitle")}</h2>
        <p className="mt-2 text-sm leading-relaxed text-muted">{t("successMessage")}</p>
      </div>
    );
  }

  return (
    <form
      method="post"
      action="#"
      onSubmit={handleSubmit}
      className="rounded-3xl border border-primary/8 bg-[#F4F6FA] p-6 sm:p-8"
    >
      <h2 className="text-xl font-semibold tracking-tight text-primary sm:text-2xl">
        {t("title")}
      </h2>
      <p className="mt-2 text-sm leading-relaxed text-muted">{t("subtitle")}</p>

      <div className="mt-6 space-y-4">
        <div>
          <label htmlFor="contact-name" className="mb-1.5 block text-sm font-medium text-primary">
            {t("name")}
          </label>
          <input
            id="contact-name"
            name="name"
            required
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={inputClass}
          />
        </div>
        <div>
          <label
            htmlFor="contact-business"
            className="mb-1.5 block text-sm font-medium text-primary"
          >
            {t("businessName")}
          </label>
          <input
            id="contact-business"
            name="business_name"
            autoComplete="organization"
            value={businessName}
            onChange={(e) => setBusinessName(e.target.value)}
            className={inputClass}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label
              htmlFor="contact-email"
              className="mb-1.5 block text-sm font-medium text-primary"
            >
              {t("email")}
            </label>
            <input
              id="contact-email"
              name="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label
              htmlFor="contact-phone"
              className="mb-1.5 block text-sm font-medium text-primary"
            >
              {t("phone")}
            </label>
            <input
              id="contact-phone"
              name="phone"
              type="tel"
              autoComplete="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className={inputClass}
            />
          </div>
        </div>
        <div>
          <label htmlFor="contact-type" className="mb-1.5 block text-sm font-medium text-primary">
            {t("inquiryType")}
          </label>
          <select
            id="contact-type"
            name="inquiry_type"
            value={inquiryType}
            onChange={(e) => setInquiryType(e.target.value as (typeof INQUIRY_TYPES)[number])}
            className={inputClass}
          >
            {INQUIRY_TYPES.map((key) => (
              <option key={key} value={key}>
                {t(`inquiryTypes.${key}`)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label
            htmlFor="contact-message"
            className="mb-1.5 block text-sm font-medium text-primary"
          >
            {t("message")}
          </label>
          <textarea
            id="contact-message"
            name="message"
            required
            rows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className={cn(inputClass, "resize-none")}
          />
        </div>
      </div>

      {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted">
          {t("responseLabel")} <span className="font-medium text-primary">{t("responseTime")}</span>
        </p>
        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-white transition-opacity disabled:opacity-60"
        >
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {submitting ? t("sending") : t("submit")}
        </button>
      </div>
    </form>
  );
}
