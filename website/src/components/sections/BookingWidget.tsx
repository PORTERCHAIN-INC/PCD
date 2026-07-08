"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import {
  MapPin,
  ArrowRight,
  Calendar,
  Package,
  Truck,
  Scale,
  Ruler,
  Sparkles,
  Circle,
  Building2,
  Zap,
  FileText,
  HeartPulse,
  Sofa,
  UtensilsCrossed,
  HardHat,
  Boxes,
  ArrowUpDown,
  Clock,
  ChevronDown,
} from "lucide-react";
import { useRouter } from "@/i18n/navigation";
import Button from "@/components/ui/Button";
import { computeAndPersistQuote, type PersistedQuoteResult } from "@/lib/quote-client";
import { createBookingDraft, getActiveBookingDraft } from "@/lib/api";
import {
  clearBookingDraftHint,
  hasBookingDraftHint,
  markBookingDraftHint,
} from "@/lib/booking-draft-hint";
import { getAnonymousSessionId } from "@/lib/anonymous-session";
import { getVisitorTracking } from "@/lib/visitor-tracking";
import VehicleIllustration, {
  resolveVehicleIllustration,
} from "@/components/illustrations/VehicleIllustration";
import { useBooking } from "@/context/BookingContext";
import AddressAutocompleteInput from "@/components/maps/AddressAutocompleteInput";
import ScheduleDateTimePicker, {
  createDefaultScheduledAt,
} from "@/components/booking/ScheduleDateTimePicker";
import BookingSelectField from "@/components/booking/BookingSelectField";
import type { BookingVehicleKey } from "@/lib/vehicle-keys";
import { cn } from "@/lib/utils";

const TAB_KEYS = ["oneTime", "business"] as const;
const TAB_ICONS = { oneTime: Zap, business: Building2 };

type WeightUnit = "kg" | "lbs";
const WEIGHT_UNITS: readonly WeightUnit[] = ["kg", "lbs"];
const LBS_TO_KG = 0.453592;

const DELIVERY_OPTIONS = [
  { key: "looseParcel", icon: Package },
  { key: "documents", icon: FileText },
  { key: "medical", icon: HeartPulse },
  { key: "furniture", icon: Sofa },
  { key: "foodBeverage", icon: UtensilsCrossed },
  { key: "construction", icon: HardHat },
  { key: "ltlPallet", icon: Boxes },
  { key: "ftlLoad", icon: Truck },
] as const;

const VEHICLE_OPTIONS = [
  { key: "sedan" },
  { key: "suv" },
  { key: "pickup" },
  { key: "cargoVan" },
  { key: "highRoof" },
  { key: "box16" },
  { key: "box20" },
] as const;

type BookingWidgetProps = {
  variant?: "default" | "compact" | "hero";
  className?: string;
};

export default function BookingWidget({ variant = "default", className }: BookingWidgetProps) {
  const isHero = variant === "hero";
  const compact = variant === "compact" || isHero;
  const t = useTranslations("booking");
  const {
    selectedVehicle,
    setSelectedVehicle,
    pickup,
    dropoff,
    setPickup,
    setDropoff,
    swapAddresses,
  } = useBooking();
  const [activeTab, setActiveTab] = useState<(typeof TAB_KEYS)[number]>("oneTime");
  const [delivery, setDelivery] = useState<string>("looseParcel");
  const [scheduleMode, setScheduleMode] = useState<"now" | "later">("now");
  const [scheduledAt, setScheduledAt] = useState(createDefaultScheduledAt);
  const [weight, setWeight] = useState("");
  const [weightUnit, setWeightUnit] = useState<WeightUnit>("kg");
  const [dimensions, setDimensions] = useState("");
  const [quote, setQuote] = useState<PersistedQuoteResult | null>(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const router = useRouter();

  // Restore in-progress checkout only when this browser session started a draft.
  useEffect(() => {
    if (!hasBookingDraftHint()) return;
    const sessionId = getAnonymousSessionId();
    getActiveBookingDraft(sessionId)
      .then((draft) => {
        if (!draft) {
          clearBookingDraftHint();
          return;
        }
        if (draft.quote_id && draft.continue_url) {
          router.replace(`/book/continue?quote_id=${draft.quote_id}&draft_id=${draft.draft_id}`);
        }
      })
      .catch(() => {
        clearBookingDraftHint();
      });
  }, [router]);

  // Persist partial progress server-side (not browser storage).
  useEffect(() => {
    if (!pickup?.formatted && !dropoff?.formatted) return;
    const sessionId = getAnonymousSessionId();
    const timer = setTimeout(() => {
      createBookingDraft({
        session_id: sessionId,
        pickup: pickup?.formatted
          ? {
              formatted: pickup.formatted,
              lat: pickup.lat,
              lng: pickup.lng,
              place_id: pickup.placeId,
            }
          : undefined,
        dropoff: dropoff?.formatted
          ? {
              formatted: dropoff.formatted,
              lat: dropoff.lat,
              lng: dropoff.lng,
              place_id: dropoff.placeId,
            }
          : undefined,
        vehicle_class: selectedVehicle,
        package_type: delivery,
        current_step: "details",
      })
        .then(() => markBookingDraftHint())
        .catch(() => {
          /* best-effort draft sync */
        });
    }, 600);
    return () => clearTimeout(timer);
  }, [pickup, dropoff, selectedVehicle, delivery]);

  async function handleInstantQuote() {
    if (!pickup?.formatted || !dropoff?.formatted) {
      setQuoteError(t("quoteError"));
      return;
    }
    setQuoteLoading(true);
    setQuoteError(null);
    setQuote(null);
    try {
      const scheduled = scheduleMode === "now" ? new Date() : scheduledAt;
      const weightRaw = weight ? parseFloat(weight.replace(/[^\d.]/g, "")) : undefined;
      const weightNum =
        weightRaw != null && !Number.isNaN(weightRaw)
          ? weightUnit === "lbs"
            ? Math.round(weightRaw * LBS_TO_KG * 100) / 100
            : weightRaw
          : undefined;
      const sessionId = getAnonymousSessionId();
      const result = await computeAndPersistQuote(
        {
          pickup: {
            formatted: pickup.formatted,
            lat: pickup.lat,
            lng: pickup.lng,
          },
          dropoff: {
            formatted: dropoff.formatted,
            lat: dropoff.lat,
            lng: dropoff.lng,
          },
          vehicleClass: selectedVehicle,
          packageType: delivery,
          weightKg: weightNum,
          dimensions: dimensions || undefined,
          scheduleMode,
          scheduledAt: scheduled,
        },
        {
          anonymous_session_id: sessionId,
          visitor_session_id: sessionId,
          tracking: getVisitorTracking(),
          pickup: {
            formatted: pickup.formatted,
            place_id: pickup.placeId,
            lat: pickup.lat,
            lng: pickup.lng,
          },
          dropoff: {
            formatted: dropoff.formatted,
            place_id: dropoff.placeId,
            lat: dropoff.lat,
            lng: dropoff.lng,
          },
          vehicle_class: selectedVehicle,
          package_type: delivery,
          weight_kg: weightNum,
          dimensions: dimensions || undefined,
        }
      );
      setQuote(result);
      markBookingDraftHint();
    } catch (err) {
      setQuoteError(err instanceof Error ? err.message : t("quoteError"));
    } finally {
      setQuoteLoading(false);
    }
  }

  function handleContinueBooking() {
    if (!quote) return;
    markBookingDraftHint();
    router.push(`/book/continue?quote_id=${quote.quote_id}`);
  }

  const Wrapper = compact ? "div" : motion.div;
  const wrapperMotionProps = compact
    ? {}
    : {
        initial: { opacity: 0, y: 24 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.65, delay: 0.25 },
      };

  return (
    <Wrapper
      {...wrapperMotionProps}
      className={cn(
        "w-full",
        compact && "booking-widget-compact flex flex-col min-h-0",
        isHero && "booking-widget-hero",
        className
      )}
    >
      <div
        className={cn(
          "relative flex flex-col min-h-0 overflow-hidden",
          compact
            ? isHero
              ? "booking-widget-panel rounded-2xl bg-white/98 border border-white/80 shadow-[0_8px_40px_-8px_rgba(10,22,40,0.35)] backdrop-blur-sm"
              : "booking-widget-panel rounded-xl sm:rounded-2xl flex-1 bg-white border border-gray-200/80 shadow-[0_4px_24px_-4px_rgba(10,22,40,0.22)]"
            : "bg-white/95 backdrop-blur-2xl border border-white/70 shadow-[0_24px_80px_-16px_rgba(10,22,40,0.4)] rounded-2xl sm:rounded-[1.75rem] md:rounded-[2rem]"
        )}
      >
        {(isHero || !compact) && (
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-secondary/50 to-transparent" />
        )}

        {/* Header + tabs */}
        <div
          className={cn(
            "flex shrink-0",
            isHero
              ? "flex-col gap-2 px-3.5 pt-3 pb-1 sm:px-4"
              : compact
                ? "flex-row items-center justify-stretch px-3 pt-2 pb-1 sm:px-4"
                : "flex-col gap-4 px-4 pt-5 pb-4 sm:px-7 sm:pt-7 md:flex-row md:items-center md:justify-between"
          )}
        >
          {isHero && (
            <h2 className="text-sm font-bold text-primary tracking-tight">{t("title")}</h2>
          )}
          {!compact && (
            <div className="min-w-0">
              <h2 className="type-h3 font-bold text-primary tracking-tight">{t("title")}</h2>
              <p className="mt-1 type-small text-muted line-clamp-2 sm:line-clamp-none">
                {t("subtitle")}
              </p>
            </div>
          )}
          <WidgetTabs
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            t={t}
            compact={compact}
            hero={isHero}
          />
        </div>

        <div
          className={cn(
            isHero
              ? "px-3.5 pb-3.5 space-y-2.5 sm:px-4 sm:pb-4"
              : compact
                ? "px-3 pb-3 space-y-2 sm:px-4 sm:pb-4"
                : "min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pb-5 space-y-4 sm:px-7 sm:pb-7 sm:space-y-5"
          )}
        >
          {/* Main row: addresses + options */}
          <div
            className={cn(
              "grid gap-2",
              isHero
                ? "grid-cols-1"
                : compact
                  ? "grid-cols-1 sm:gap-3"
                  : "md:grid-cols-2 gap-4 md:gap-5"
            )}
          >
            {/* Uber-style address route */}
            <div
              className={cn(
                "relative rounded-xl bg-gray-bg/80 border border-gray-200/60",
                isHero ? "p-2" : compact ? "p-2.5 sm:p-3" : "rounded-2xl p-4 sm:p-5"
              )}
            >
              <button
                type="button"
                onClick={swapAddresses}
                aria-label={t("swapAddresses")}
                className={cn(
                  "absolute right-1.5 sm:right-2 top-1/2 -translate-y-1/2 z-10 touch-target rounded-full bg-white border border-gray-200/80 flex items-center justify-center text-muted hover:text-secondary hover:border-secondary/40 hover:shadow-md transition-all cursor-pointer",
                  isHero ? "w-8 h-8" : compact ? "w-9 h-9" : "w-11 h-11 right-2 sm:right-3"
                )}
              >
                <ArrowUpDown className="w-3 h-3" />
              </button>

              <div
                className={cn(
                  "flex gap-2",
                  isHero ? "pr-9" : compact ? "pr-10 sm:pr-11" : "gap-3 pr-12 sm:pr-14"
                )}
              >
                {/* Route line */}
                <div className="flex flex-col items-center pt-1.5 pb-1.5 shrink-0">
                  <div className="booking-icon-badge bg-secondary/15 text-secondary">
                    <Circle
                      className={cn(
                        isHero ? "w-2.5 h-2.5" : compact ? "w-3 h-3" : "w-4 h-4",
                        "fill-secondary text-secondary"
                      )}
                    />
                  </div>
                  <div className="w-0.5 flex-1 min-h-[0.85rem] my-0.5 bg-gradient-to-b from-secondary/50 to-primary/30 rounded-full" />
                  <div className="booking-icon-badge bg-primary/10 text-primary">
                    <MapPin className={isHero ? "w-2.5 h-2.5" : compact ? "w-3 h-3" : "w-4 h-4"} />
                  </div>
                </div>

                {/* Inputs */}
                <div
                  className={cn(
                    "flex-1 flex flex-col min-w-0",
                    isHero ? "gap-1.5" : compact ? "gap-2" : "gap-3"
                  )}
                >
                  <div className="group">
                    {!isHero && (
                      <label className="type-caption font-bold text-muted mb-1 block normal-case">
                        {t("pickupAddress")}
                      </label>
                    )}
                    <AddressAutocompleteInput
                      id="booking-pickup"
                      value={pickup?.formatted ?? ""}
                      onChange={(value) => setPickup(value ? { formatted: value } : null)}
                      onPlaceSelect={setPickup}
                      placeholder={t("pickupPlaceholder")}
                    />
                  </div>
                  <div className="group">
                    {!isHero && (
                      <label className="type-caption font-bold text-muted mb-1 block normal-case">
                        {t("dropoffAddress")}
                      </label>
                    )}
                    <AddressAutocompleteInput
                      id="booking-dropoff"
                      value={dropoff?.formatted ?? ""}
                      onChange={(value) => setDropoff(value ? { formatted: value } : null)}
                      onPlaceSelect={setDropoff}
                      placeholder={t("dropoffPlaceholder")}
                    />
                  </div>
                </div>
              </div>
            </div>

            {compact && (
              <DeliveryVehicleFields
                compact
                hero={isHero}
                delivery={delivery}
                setDelivery={setDelivery}
                selectedVehicle={selectedVehicle}
                setSelectedVehicle={setSelectedVehicle}
                t={t}
              />
            )}

            {/* Schedule + package */}
            <div className={cn("flex flex-col", isHero ? "gap-2" : compact ? "gap-2" : "gap-4")}>
              <div
                className={cn(
                  "rounded-xl bg-gray-bg/80 border border-gray-200/60",
                  isHero ? "p-2" : compact ? "p-2.5 sm:p-3" : "rounded-2xl p-4 sm:p-5"
                )}
              >
                {!isHero && (
                  <span className="type-caption font-bold text-muted mb-2 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" />
                    {t("schedule")}
                  </span>
                )}
                <div className={cn("flex gap-1.5", isHero ? "mb-1.5" : "mb-2")}>
                  <button
                    type="button"
                    onClick={() => setScheduleMode("now")}
                    className={cn(
                      "booking-chip flex-1 justify-center",
                      scheduleMode === "now" ? "booking-chip-active" : "booking-chip-inactive"
                    )}
                  >
                    <Zap className="w-3.5 h-3.5" />
                    {t("deliverNow")}
                  </button>
                  <button
                    type="button"
                    onClick={() => setScheduleMode("later")}
                    className={cn(
                      "booking-chip flex-1 justify-center",
                      scheduleMode === "later" ? "booking-chip-active" : "booking-chip-inactive"
                    )}
                  >
                    <Calendar className="w-3.5 h-3.5" />
                    {t("scheduleLater")}
                  </button>
                </div>
                {scheduleMode === "later" && (
                  <ScheduleDateTimePicker
                    value={scheduledAt}
                    onChange={setScheduledAt}
                    compact={compact}
                    hero={isHero}
                  />
                )}

                <div
                  className={cn(
                    isHero
                      ? "mt-1.5 pt-1.5 border-t border-gray-200/50"
                      : compact
                        ? "mt-2 pt-2 border-t border-gray-200/60"
                        : "mt-0"
                  )}
                >
                  {!compact && (
                    <span className="type-caption font-bold text-muted mb-2 block">
                      {t("packageDetails")}
                    </span>
                  )}
                  <div className="flex gap-1.5">
                    <div className="flex items-center gap-1 flex-1 bg-white rounded-lg pl-2.5 pr-1 py-1.5 border border-gray-200/60 focus-within:border-secondary/40 focus-within:ring-2 focus-within:ring-secondary/15 transition-all">
                      <Scale className="w-3 h-3 text-secondary shrink-0" />
                      <input
                        type="text"
                        inputMode="decimal"
                        placeholder={t("weight")}
                        value={weight}
                        onChange={(e) => setWeight(e.target.value)}
                        className={cn(
                          "w-full min-w-0 bg-transparent text-primary placeholder:text-muted/50 outline-none",
                          isHero ? "text-xs" : "text-sm"
                        )}
                      />
                      <WeightUnitToggle unit={weightUnit} onChange={setWeightUnit} hero={isHero} />
                    </div>
                    <div className="flex items-center gap-1 flex-[1.2] bg-white rounded-lg px-2.5 py-1.5 border border-gray-200/60 focus-within:border-secondary/40 focus-within:ring-2 focus-within:ring-secondary/15 transition-all">
                      <Ruler className="w-3 h-3 text-secondary shrink-0" />
                      <input
                        type="text"
                        placeholder={t("dimensions")}
                        value={dimensions}
                        onChange={(e) => setDimensions(e.target.value)}
                        className={cn(
                          "w-full bg-transparent text-primary placeholder:text-muted/50 outline-none",
                          isHero ? "text-xs" : "text-sm"
                        )}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {!compact && (
                <div className="rounded-2xl bg-gray-bg/80 border border-gray-200/60 p-4 sm:p-5 flex-1">
                  <span className="type-caption font-bold text-muted mb-3 block">
                    {t("packageDetails")}
                  </span>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <div className="flex items-center gap-2 flex-1 bg-white rounded-full pl-4 pr-1.5 py-3 border border-gray-200/60 focus-within:border-secondary/40 focus-within:ring-2 focus-within:ring-secondary/15 transition-all">
                      <Scale className="w-4 h-4 text-secondary shrink-0" />
                      <input
                        type="text"
                        inputMode="decimal"
                        placeholder={t("weight")}
                        value={weight}
                        onChange={(e) => setWeight(e.target.value)}
                        className="w-full min-w-0 bg-transparent text-base text-primary placeholder:text-muted/50 outline-none"
                      />
                      <WeightUnitToggle unit={weightUnit} onChange={setWeightUnit} />
                    </div>
                    <div className="flex items-center gap-2 flex-[1.4] bg-white rounded-full px-4 py-3 border border-gray-200/60 focus-within:border-secondary/40 focus-within:ring-2 focus-within:ring-secondary/15 transition-all">
                      <Ruler className="w-4 h-4 text-secondary shrink-0" />
                      <input
                        type="text"
                        placeholder={t("dimensions")}
                        value={dimensions}
                        onChange={(e) => setDimensions(e.target.value)}
                        className="w-full bg-transparent text-base text-primary placeholder:text-muted/50 outline-none"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {!compact && (
            <DeliveryVehicleFields
              compact={false}
              delivery={delivery}
              setDelivery={setDelivery}
              selectedVehicle={selectedVehicle}
              setSelectedVehicle={setSelectedVehicle}
              t={t}
            />
          )}

          {/* CTA */}
          <Button
            shape="pill"
            size={isHero ? "sm" : compact ? "md" : "lg"}
            type="button"
            disabled={quoteLoading}
            onClick={handleInstantQuote}
            className={cn(
              "w-full font-bold gap-2 bg-gradient-to-r from-secondary to-[#1d4ed8] hover:from-[#1d4ed8] hover:to-[#1e40af] shadow-lg shadow-secondary/25 group",
              isHero
                ? "min-h-9 text-xs shadow-md"
                : compact
                  ? "min-h-10 text-sm"
                  : "min-h-[3.5rem] sm:min-h-[3.75rem] text-base gap-3 shadow-xl shadow-secondary/30"
            )}
          >
            <span
              className={cn(
                "flex items-center justify-center rounded-full bg-white/20",
                isHero ? "w-6 h-6" : compact ? "w-7 h-7" : "w-9 h-9"
              )}
            >
              <Sparkles className={isHero ? "w-3.5 h-3.5" : compact ? "w-4 h-4" : "w-5 h-5"} />
            </span>
            {quoteLoading ? t("quoteLoading") : t("instantQuote")}
            <ArrowRight
              className={cn(
                compact ? "w-4 h-4" : "w-5 h-5",
                "group-hover:translate-x-1 transition-transform"
              )}
            />
          </Button>

          {quoteError && <p className="text-center type-caption text-red-600">{quoteError}</p>}

          {quote && (
            <div
              className={cn(
                "rounded-xl bg-secondary/5 border border-secondary/20",
                compact ? "p-2.5 space-y-2" : "rounded-2xl p-4 space-y-3"
              )}
            >
              {compact ? (
                <>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-primary">
                        {t("quoteResult", { amount: quote.amount_display })}
                      </p>
                      <p className="text-xs text-muted">
                        {quote.distance_km != null &&
                          t("quoteDistance", { distance: quote.distance_km.toFixed(1) })}
                        {quote.website_quote?.recommendedVehicle &&
                          ` · ${quote.website_quote.recommendedVehicle.name}`}
                      </p>
                    </div>
                    <Button
                      shape="pill"
                      size="sm"
                      type="button"
                      onClick={handleContinueBooking}
                      className="shrink-0 font-bold"
                    >
                      {t("continueBooking")}
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                  <p className="text-xs text-muted text-center">
                    {t("quoteExpires", {
                      time: new Date(quote.expires_at).toLocaleTimeString(undefined, {
                        hour: "numeric",
                        minute: "2-digit",
                      }),
                    })}
                  </p>
                </>
              ) : (
                <>
                  <div className="text-center space-y-1">
                    <p className="type-body font-bold text-primary">
                      {t("quoteResult", { amount: quote.amount_display })}
                    </p>
                    {quote.distance_km != null && (
                      <p className="type-caption text-muted">
                        {t("quoteDistance", { distance: quote.distance_km.toFixed(1) })}
                      </p>
                    )}
                    {quote.website_quote?.recommendedVehicle && (
                      <p className="type-caption text-muted">
                        {t("quoteVehicle", {
                          vehicle: quote.website_quote.recommendedVehicle.name,
                        })}
                      </p>
                    )}
                  </div>

                  {quote.pricing_breakdown && quote.pricing_breakdown.length > 0 && (
                    <ul className="rounded-xl bg-white/70 border border-secondary/10 divide-y divide-secondary/10 text-left">
                      {quote.pricing_breakdown.map((line) => (
                        <li
                          key={line.code}
                          className="flex items-center justify-between gap-3 px-3 py-2 type-caption"
                        >
                          <span className="text-muted">{line.label}</span>
                          <span className="font-semibold text-primary tabular-nums">
                            ${(line.amount_cents / 100).toFixed(2)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}

                  <p className="text-center type-caption text-muted">
                    {t("quoteExpires", {
                      time: new Date(quote.expires_at).toLocaleTimeString(undefined, {
                        hour: "numeric",
                        minute: "2-digit",
                      }),
                    })}
                  </p>
                  <Button
                    shape="pill"
                    size="md"
                    type="button"
                    onClick={handleContinueBooking}
                    className="w-full font-bold"
                  >
                    {t("continueBooking")}
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </>
              )}
            </div>
          )}

          {!compact && (
            <p className="text-center type-caption normal-case tracking-normal text-muted flex items-center justify-center gap-1">
              <ChevronDown className="w-3 h-3 opacity-50" />
              {t("quoteNote")}
            </p>
          )}
        </div>
      </div>
    </Wrapper>
  );
}

function DeliveryVehicleFields({
  compact,
  hero = false,
  delivery,
  setDelivery,
  selectedVehicle,
  setSelectedVehicle,
  t,
}: {
  compact: boolean;
  hero?: boolean;
  delivery: string;
  setDelivery: (value: string) => void;
  selectedVehicle: BookingVehicleKey;
  setSelectedVehicle: (value: BookingVehicleKey) => void;
  t: (key: string) => string;
}) {
  const deliveryOptions = DELIVERY_OPTIONS.map(({ key }) => ({
    value: key,
    label: t(`deliveryOptions.${key}`),
  }));
  const vehicleOptions = VEHICLE_OPTIONS.map(({ key }) => ({
    value: key,
    label: t(`vehicleOptions.${key}`),
  }));

  if (compact) {
    return (
      <div className={cn("grid gap-2", hero ? "grid-cols-1" : "grid-cols-2")}>
        <BookingSelectField
          id="booking-delivery-type"
          label={hero ? undefined : t("deliveryType")}
          icon={Package}
          value={delivery}
          options={deliveryOptions}
          onChange={setDelivery}
          compact
          hero={hero}
        />
        <BookingSelectField
          id="booking-vehicle-type"
          label={hero ? undefined : t("vehicleType")}
          icon={Truck}
          value={selectedVehicle}
          options={vehicleOptions}
          onChange={(value) => setSelectedVehicle(value as BookingVehicleKey)}
          compact
          hero={hero}
        />
      </div>
    );
  }

  return (
    <>
      <div className="md:hidden grid grid-cols-1 sm:grid-cols-2 gap-3">
        <BookingSelectField
          id="booking-delivery-type-mobile"
          label={t("deliveryType")}
          icon={Package}
          value={delivery}
          options={deliveryOptions}
          onChange={setDelivery}
        />
        <BookingSelectField
          id="booking-vehicle-type-mobile"
          label={t("vehicleType")}
          icon={Truck}
          value={selectedVehicle}
          options={vehicleOptions}
          onChange={(value) => setSelectedVehicle(value as BookingVehicleKey)}
        />
      </div>

      <div className="hidden md:grid md:grid-cols-2 gap-5">
        <div>
          <span className="type-caption font-bold text-muted mb-2 flex items-center gap-1.5">
            <Package className="w-3.5 h-3.5" />
            {t("deliveryType")}
          </span>
          <div className="scroll-row scroll-row-fade -mx-1 px-1">
            {DELIVERY_OPTIONS.map(({ key, icon: Icon }) => (
              <button
                key={key}
                type="button"
                onClick={() => setDelivery(key)}
                className={cn(
                  "booking-chip",
                  delivery === key ? "booking-chip-active" : "booking-chip-inactive"
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {t(`deliveryOptions.${key}`)}
              </button>
            ))}
          </div>
        </div>

        <div>
          <span className="type-caption font-bold text-muted mb-2 flex items-center gap-1.5">
            <Truck className="w-3.5 h-3.5" />
            {t("vehicleType")}
          </span>
          <div className="scroll-row scroll-row-fade -mx-1 px-1">
            {VEHICLE_OPTIONS.map(({ key }) => (
              <button
                key={key}
                type="button"
                onClick={() => setSelectedVehicle(key as BookingVehicleKey)}
                className={cn(
                  "booking-chip",
                  selectedVehicle === key ? "booking-chip-active" : "booking-chip-inactive"
                )}
              >
                <VehicleIllustration
                  type={resolveVehicleIllustration(key)}
                  id={`chip-${key}`}
                  mode="icon"
                  className="w-7 h-5 shrink-0 rounded object-cover opacity-90"
                />
                {t(`vehicleOptions.${key}`)}
              </button>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

function WeightUnitToggle({
  unit,
  onChange,
  hero = false,
}: {
  unit: WeightUnit;
  onChange: (unit: WeightUnit) => void;
  hero?: boolean;
}) {
  return (
    <div
      className="flex shrink-0 rounded-full bg-gray-bg p-0.5"
      role="group"
      aria-label="Weight unit"
    >
      {WEIGHT_UNITS.map((u) => (
        <button
          key={u}
          type="button"
          aria-pressed={unit === u}
          onClick={() => onChange(u)}
          className={cn(
            "rounded-full font-bold uppercase tracking-wide transition-all cursor-pointer",
            hero ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-1 text-xs",
            unit === u ? "bg-secondary text-white shadow-sm" : "text-muted hover:text-primary"
          )}
        >
          {u}
        </button>
      ))}
    </div>
  );
}

function WidgetTabs({
  activeTab,
  setActiveTab,
  t,
  compact = false,
  hero = false,
}: {
  activeTab: (typeof TAB_KEYS)[number];
  setActiveTab: (tab: (typeof TAB_KEYS)[number]) => void;
  t: (key: string) => string;
  compact?: boolean;
  hero?: boolean;
}) {
  const router = useRouter();

  return (
    <div
      className={cn(
        "flex p-0.5 rounded-full bg-gray-bg border border-gray-200/80 shrink-0",
        compact ? "w-full sm:w-auto" : "w-full sm:w-auto"
      )}
    >
      {TAB_KEYS.map((tab) => {
        const Icon = TAB_ICONS[tab];
        const isActive = activeTab === tab;
        return (
          <button
            key={tab}
            type="button"
            onClick={() => {
              if (tab === "business") {
                router.push("/business");
                return;
              }
              setActiveTab(tab);
            }}
            className={cn(
              "relative flex flex-1 sm:flex-none items-center justify-center gap-1.5 type-nav-strong rounded-full transition-all cursor-pointer whitespace-nowrap",
              hero
                ? "px-2.5 py-1 min-h-7 text-[11px]"
                : compact
                  ? "px-3 py-1.5 min-h-8 text-xs"
                  : "gap-2 px-4 sm:px-5 py-2.5 min-h-[2.75rem]",
              isActive
                ? "bg-white text-secondary font-bold shadow-md shadow-secondary/10"
                : "text-muted hover:text-primary hover:font-bold"
            )}
          >
            <Icon
              className={cn(
                "shrink-0",
                compact ? "w-3.5 h-3.5" : "w-4 h-4",
                isActive && "text-secondary"
              )}
            />
            <span>{t(`tabs.${tab}`)}</span>
          </button>
        );
      })}
    </div>
  );
}
