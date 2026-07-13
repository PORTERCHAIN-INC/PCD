"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { Check, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";
import { submitInquiry } from "@/lib/submit-inquiry";
import { getStoredAttribution, resolveLeadSource } from "@/lib/seo/attribution";
import { pushAttributionToZoho } from "@/lib/seo/zoho-attribution";
import WhatsAppQuoteLink from "@/components/seo/WhatsAppQuoteLink";
import { buildQuoteWhatsAppMessage } from "@/lib/whatsapp";

const INQUIRY_TYPES = ["sales", "support", "partnership", "careers", "api"] as const;
type InquiryType = (typeof INQUIRY_TYPES)[number];

const QUOTE_URGENCY_KEYS = ["sameDay", "urgent", "scheduled", "unsure"] as const;
const QUOTE_VEHICLE_KEYS = [
  "unsure",
  "sedan",
  "suv",
  "pickup",
  "cargoVan",
  "highRoof",
  "box16",
  "box20",
] as const;

interface ContactInquiryFormProps {
  intent?: string;
  attributionFrom?: string;
}

export default function ContactInquiryForm({ intent, attributionFrom }: ContactInquiryFormProps) {
  const t = useTranslations("corporate.contact.form");
  const [submitted, setSubmitted] = useState(false);
  const [whatsappMessage, setWhatsappMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inquiryType, setInquiryType] = useState<InquiryType>("sales");
  const isDemo = intent === "demo";
  const isQuote = intent === "quote";

  useEffect(() => {
    if (isDemo || isQuote) {
      setInquiryType("sales");
    }
  }, [isDemo, isQuote]);

  useEffect(() => {
    if (attributionFrom === "vehicle-partner") {
      setInquiryType("partnership");
    }
  }, [attributionFrom]);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const form = e.currentTarget;
    const data = new FormData(form);
    const name = String(data.get("name") ?? "");
    const businessName = String(data.get("businessName") ?? "");
    const email = String(data.get("email") ?? "");
    const phone = String(data.get("phone") ?? "");
    const message = String(data.get("message") ?? "");
    const urgency = String(data.get("urgency") ?? "");
    const vehicle = String(data.get("vehicle") ?? "");
    const lanes = String(data.get("lanes") ?? "");

    const leadSource = resolveLeadSource(attributionFrom);
    const stored = getStoredAttribution();
    const intentLabel = isQuote ? "quote" : isDemo ? "demo" : inquiryType;

    const quoteDetails = isQuote
      ? [
          urgency ? `Urgency: ${urgency}` : null,
          vehicle ? `Vehicle: ${vehicle}` : null,
          lanes ? `Lanes: ${lanes}` : null,
        ]
          .filter(Boolean)
          .join("\n")
      : "";

    const fullMessage = [quoteDetails, message].filter(Boolean).join("\n\n");

    pushAttributionToZoho({ ...stored, from: leadSource });

    try {
      await submitInquiry({
        name,
        email,
        phone: phone || undefined,
        business_name: businessName || undefined,
        message: fullMessage,
        intent: intentLabel,
        inquiry_type: inquiryType,
        source: "website",
        source_page: leadSource,
        form: "contact",
        utm_source: stored.utm_source,
        utm_campaign: stored.utm_campaign,
        utm_medium: stored.utm_medium,
      });
    } catch {
      setError(t("errorMessage"));
      setLoading(false);
      return;
    }

    const eventName = isQuote
      ? ANALYTICS_EVENTS.QUOTE_REQUEST
      : isDemo
        ? ANALYTICS_EVENTS.DEMO_REQUEST
        : ANALYTICS_EVENTS.CONTACT_FORM_SUBMIT_SUCCESS;
    track(eventName, {
      inquiry_type: inquiryType,
      source_section: "contact_page",
      ...(leadSource ? { source_page: leadSource, from: leadSource } : {}),
      ...(stored.utm_source ? { utm_source: stored.utm_source } : {}),
      ...(stored.utm_campaign ? { utm_campaign: stored.utm_campaign } : {}),
      ...(isQuote ? { intent: "quote" } : {}),
      ...(isDemo ? { intent: "demo" } : {}),
    });
    setLoading(false);
    if (isQuote) {
      setWhatsappMessage(
        buildQuoteWhatsAppMessage({
          name,
          businessName,
          urgency,
          vehicle,
          lanes,
          source: leadSource,
        })
      );
    }
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
        <h3 className="text-xl font-semibold text-primary">
          {isQuote ? t("quote.successTitle") : t("successTitle")}
        </h3>
        <p className="mt-2 text-sm text-muted leading-relaxed max-w-sm">
          {isQuote ? t("quote.successMessage") : t("successMessage")}
        </p>
        {isQuote && whatsappMessage && (
          <WhatsAppQuoteLink
            className="mt-6 w-full max-w-sm"
            message={whatsappMessage}
            label={t("quote.whatsappCta")}
            hint={t("quote.whatsappHint")}
            sourceSection="contact_quote_success"
          />
        )}
      </motion.div>
    );
  }

  return (
    <div>
      <form onSubmit={handleSubmit} className="card-surface p-6 sm:p-8 space-y-5">
        <div>
          <h2 className="text-xl font-semibold text-primary tracking-tight">
            {isQuote ? t("quote.title") : t("title")}
          </h2>
          <p className="mt-1.5 text-sm text-muted">
            {isQuote ? t("quote.subtitle") : t("subtitle")}
          </p>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <Field label={t("name")} name="name" required autoComplete="name" />
          <Field label={t("businessName")} name="businessName" autoComplete="organization" />
          <Field label={t("email")} name="email" type="email" required autoComplete="email" />
          <Field label={t("phone")} name="phone" type="tel" autoComplete="tel" />
        </div>

        {isQuote && (
          <>
            <div className="grid sm:grid-cols-2 gap-4">
              <SelectField
                label={t("quote.urgency")}
                name="urgency"
                required
                placeholder={t("quote.urgencyPlaceholder")}
                options={QUOTE_URGENCY_KEYS.map((key) => ({
                  value: t(`quote.urgencyOptions.${key}`),
                  label: t(`quote.urgencyOptions.${key}`),
                }))}
              />
              <SelectField
                label={t("quote.vehicle")}
                name="vehicle"
                placeholder={t("quote.vehiclePlaceholder")}
                options={QUOTE_VEHICLE_KEYS.map((key) => ({
                  value: t(`quote.vehicleOptions.${key}`),
                  label: t(`quote.vehicleOptions.${key}`),
                }))}
              />
            </div>
            <Field
              label={t("quote.lanes")}
              name="lanes"
              required
              placeholder={t("quote.lanesPlaceholder")}
            />
          </>
        )}

        <div>
          <label htmlFor="message" className="block text-sm font-medium text-primary mb-1.5">
            {isQuote ? t("quote.message") : t("message")}
            {!isQuote && <span className="text-secondary ml-0.5">*</span>}
          </label>
          <textarea
            id="message"
            name="message"
            rows={4}
            required={!isQuote}
            className="w-full rounded-xl border border-primary/10 px-4 py-3 text-sm text-primary outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/15 resize-none transition-shadow"
          />
        </div>

        {!isQuote && (
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
        )}

        <button
          type="submit"
          disabled={loading}
          className={cn(
            "w-full py-3.5 rounded-full bg-secondary text-white font-semibold text-sm",
            "hover:bg-[#1d4ed8] transition-all hover:shadow-lg hover:shadow-secondary/25",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          {loading ? t("sending") : isQuote ? t("quote.submit") : t("submit")}
        </button>
        {error && (
          <p className="text-sm text-red-600 text-center" role="alert">
            {error}
          </p>
        )}
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
  placeholder,
}: {
  label: string;
  name: string;
  type?: string;
  required?: boolean;
  autoComplete?: string;
  placeholder?: string;
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
        placeholder={placeholder}
        className="w-full rounded-xl border border-primary/10 px-4 py-2.5 text-sm text-primary outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/15 min-h-[2.75rem] transition-shadow bg-white"
      />
    </div>
  );
}

function SelectField({
  label,
  name,
  required,
  placeholder,
  options,
}: {
  label: string;
  name: string;
  required?: boolean;
  placeholder: string;
  options: { value: string; label: string }[];
}) {
  return (
    <div>
      <label htmlFor={name} className="block text-sm font-medium text-primary mb-1.5">
        {label}
        {required && <span className="text-secondary ml-0.5">*</span>}
      </label>
      <select
        id={name}
        name={name}
        required={required}
        defaultValue=""
        className="w-full rounded-xl border border-primary/10 px-4 py-2.5 text-sm text-primary outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/15 min-h-[2.75rem] transition-shadow bg-white"
      >
        <option value="" disabled>
          {placeholder}
        </option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
