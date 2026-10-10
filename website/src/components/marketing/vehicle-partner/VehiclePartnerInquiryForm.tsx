"use client";

import { useState, type FormEvent } from "react";
import { motion } from "framer-motion";
import { useLocale, useTranslations } from "next-intl";
import { Check, ExternalLink, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";
import { submitInquiry } from "@/lib/submit-inquiry";
import MarketingConsentCheckbox from "@/components/forms/MarketingConsentCheckbox";
import { useFormGuard } from "@/components/forms/useFormGuard";
import { getStoredAttribution } from "@/lib/seo/attribution";
import { driverPortalUrl } from "@/data/portal-links";
import LinkButton from "@/components/marketing/corporate/ui/LinkButton";

const COUNTRY_CODES = [
  { code: "+1", label: "CA +1" },
  { code: "+1", label: "US +1" },
  { code: "+44", label: "UK +44" },
  { code: "+33", label: "FR +33" },
  { code: "+49", label: "DE +49" },
  { code: "+91", label: "IN +91" },
] as const;

const VEHICLE_KEYS = ["sedan", "pickup", "van", "boxTruck", "box20", "unsure"] as const;

const inputClass =
  "w-full rounded-xl border border-primary/10 px-4 py-3 text-sm text-primary outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/15 transition-shadow";

interface VehiclePartnerInquiryFormProps {
  id?: string;
  className?: string;
  onInteractionChange?: (active: boolean) => void;
}

export default function VehiclePartnerInquiryForm({
  id = "apply",
  className,
  onInteractionChange,
}: VehiclePartnerInquiryFormProps) {
  const t = useTranslations("vehiclePartner.inquiry");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [extension, setExtension] = useState("");
  const [countryCode, setCountryCode] = useState("+1");
  const [vehicleType, setVehicleType] = useState("");
  const [serviceArea, setServiceArea] = useState("");
  const [notes, setNotes] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [marketingConsent, setMarketingConsent] = useState(false);
  const locale = useLocale();
  const { guardFields, honeypotField } = useFormGuard();
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name || !email || !phone || !agreed) return;

    setSubmitting(true);
    setError(null);

    const fullPhone = `${countryCode} ${phone}${extension ? ` ext. ${extension}` : ""}`;
    const vehicleLabel = vehicleType
      ? t(`vehicles.${vehicleType as (typeof VEHICLE_KEYS)[number]}`)
      : "";
    const message = [
      vehicleLabel ? `Vehicle: ${vehicleLabel}` : null,
      serviceArea.trim() ? `Service area: ${serviceArea.trim()}` : null,
      notes.trim() ? notes.trim() : null,
    ]
      .filter(Boolean)
      .join("\n");

    const stored = getStoredAttribution();

    try {
      await submitInquiry({
        name,
        email,
        phone: fullPhone,
        message: message || undefined,
        intent: "driver_partner",
        inquiry_type: "partnership",
        source: "website",
        source_page: "/vehicle-partner",
        form: "vehicle_partner",
        utm_source: stored.utm_source,
        utm_campaign: stored.utm_campaign,
        utm_medium: stored.utm_medium,
        // Required "contact me about the program" box — now stored as evidence.
        contact_consent: agreed,
        marketing_consent: marketingConsent,
        locale,
        ...guardFields(),
      });
    } catch {
      setError(t("errorMessage"));
      setSubmitting(false);
      return;
    }

    track(ANALYTICS_EVENTS.DRIVER_PARTNER_INQUIRY_SUBMIT, {
      source_section: "vehicle_partner_form",
      vehicle_type: vehicleType || undefined,
    });
    setSubmitting(false);
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <motion.div
        id={id}
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        className={cn("card-surface p-8 sm:p-10 text-center", className)}
      >
        <div className="w-14 h-14 rounded-full bg-secondary/10 flex items-center justify-center mx-auto mb-5">
          <Check className="w-7 h-7 text-secondary" />
        </div>
        <h3 className="text-xl font-semibold text-primary">{t("successTitle")}</h3>
        <p className="mt-2 text-sm text-muted leading-relaxed">{t("successMessage")}</p>
        <div className="mt-6 space-y-2">
          <LinkButton
            href={driverPortalUrl}
            size="lg"
            external
            className="w-full max-w-sm mx-auto"
            trackSource="vehicle_partner_success"
            trackLabel={t("portalCta")}
          >
            {t("portalCta")}
            <ExternalLink className="w-4 h-4 ml-1.5" />
          </LinkButton>
          <p className="text-xs text-muted max-w-sm mx-auto">{t("portalHint")}</p>
        </div>
      </motion.div>
    );
  }

  return (
    <div
      id={id}
      className={cn("card-surface p-6 sm:p-8", className)}
      onFocusCapture={() => onInteractionChange?.(true)}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          onInteractionChange?.(false);
        }
      }}
    >
      <div className="mb-6">
        <h2 className="text-xl sm:text-2xl font-semibold text-primary tracking-tight">
          {t("title")}
        </h2>
        <p className="mt-2 text-sm text-muted leading-relaxed">{t("subtitle")}</p>
      </div>

      <form onSubmit={handleSubmit} className="relative space-y-4" noValidate>
        {honeypotField}
        <div>
          <label htmlFor={`${id}-name`} className="block text-sm font-medium text-primary mb-1.5">
            {t("name")} <span className="text-secondary">*</span>
          </label>
          <input
            id={`${id}-name`}
            name="name"
            type="text"
            required
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("namePlaceholder")}
            className={inputClass}
          />
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label
              htmlFor={`${id}-email`}
              className="block text-sm font-medium text-primary mb-1.5"
            >
              {t("email")} <span className="text-secondary">*</span>
            </label>
            <input
              id={`${id}-email`}
              name="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={t("emailPlaceholder")}
              className={inputClass}
            />
          </div>

          <div>
            <label
              htmlFor={`${id}-vehicle`}
              className="block text-sm font-medium text-primary mb-1.5"
            >
              {t("vehicleType")}
            </label>
            <select
              id={`${id}-vehicle`}
              name="vehicleType"
              value={vehicleType}
              onChange={(e) => setVehicleType(e.target.value)}
              className={cn(inputClass, "cursor-pointer")}
            >
              <option value="">{t("vehicleTypePlaceholder")}</option>
              {VEHICLE_KEYS.map((key) => (
                <option key={key} value={key}>
                  {t(`vehicles.${key}`)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label htmlFor={`${id}-phone`} className="block text-sm font-medium text-primary mb-1.5">
            {t("phone")} <span className="text-secondary">*</span>
          </label>
          <div className="flex min-w-0 items-stretch gap-2">
            <select
              aria-label={t("countryCode")}
              value={countryCode}
              onChange={(e) => setCountryCode(e.target.value)}
              className={cn(inputClass, "shrink-0 w-[6.75rem] cursor-pointer")}
            >
              {COUNTRY_CODES.map((c) => (
                <option key={c.label} value={c.code}>
                  {c.label}
                </option>
              ))}
            </select>
            <input
              id={`${id}-phone`}
              name="phone"
              type="tel"
              required
              autoComplete="tel-national"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder={t("phonePlaceholder")}
              className={cn(inputClass, "min-w-0 flex-1 basis-0")}
            />
            <input
              id={`${id}-ext`}
              name="extension"
              type="text"
              inputMode="numeric"
              aria-label={t("extension")}
              value={extension}
              onChange={(e) => setExtension(e.target.value)}
              placeholder={t("extensionShort")}
              className={cn(inputClass, "shrink-0 w-[4.75rem] sm:w-[5.25rem] px-2.5 text-center")}
            />
          </div>
          <p className="mt-1.5 text-xs text-muted">
            {t("extension")} <span className="text-muted">({t("optional")})</span>
          </p>
        </div>

        <div>
          <label htmlFor={`${id}-area`} className="block text-sm font-medium text-primary mb-1.5">
            {t("serviceArea")}
          </label>
          <input
            id={`${id}-area`}
            name="serviceArea"
            type="text"
            value={serviceArea}
            onChange={(e) => setServiceArea(e.target.value)}
            placeholder={t("serviceAreaPlaceholder")}
            className={inputClass}
          />
        </div>

        <div>
          <label htmlFor={`${id}-notes`} className="block text-sm font-medium text-primary mb-1.5">
            {t("notes")}
          </label>
          <textarea
            id={`${id}-notes`}
            name="notes"
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder={t("notesPlaceholder")}
            className={cn(inputClass, "resize-none")}
          />
        </div>

        <label className="flex items-start gap-3 cursor-pointer group py-1 min-h-[2.75rem]">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
            className="mt-0.5 w-5 h-5 shrink-0 rounded border-primary/20 text-secondary focus:ring-secondary/30"
            required
          />
          <span className="text-sm text-muted group-hover:text-primary transition-colors leading-relaxed">
            {t("consent")}
          </span>
        </label>

        <MarketingConsentCheckbox
          id="vehicle-partner-marketing-consent"
          checked={marketingConsent}
          onChange={setMarketingConsent}
        />

        <button
          type="submit"
          disabled={submitting || !agreed}
          className="w-full flex items-center justify-center gap-2 min-h-[2.75rem] px-6 py-3.5 rounded-xl bg-secondary text-white font-semibold text-sm hover:bg-secondary/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
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
          {(["noObligation", "gLicence", "responseTime"] as const).map((key) => (
            <li key={key} className="flex items-center gap-1.5 text-xs text-muted">
              <Check className="w-3.5 h-3.5 text-secondary" />
              {t(`assurances.${key}`)}
            </li>
          ))}
        </ul>
      </form>
    </div>
  );
}
