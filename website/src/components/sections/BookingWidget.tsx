"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
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
import { createQuote, type QuoteResult } from "@/lib/api";
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
import type { BookingVehicleKey } from "@/lib/vehicle-keys";

import { cn } from "@/lib/utils";

const TAB_KEYS = ["oneTime", "business"] as const;
const TAB_ICONS = { oneTime: Zap, business: Building2 };

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

export default function BookingWidget() {
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
  const [dimensions, setDimensions] = useState("");
  const [quote, setQuote] = useState<QuoteResult | null>(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const router = useRouter();

  async function handleInstantQuote() {
    if (!pickup?.formatted || !dropoff?.formatted) {
      setQuoteError(t("quoteError"));
      return;
    }
    setQuoteLoading(true);
    setQuoteError(null);
    setQuote(null);
    try {
      const scheduled =
        scheduleMode === "now" ? new Date() : scheduledAt;
      const weightNum = weight ? parseFloat(weight.replace(/[^\d.]/g, "")) : undefined;
      const sessionId = getAnonymousSessionId();
      const result = await createQuote({
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
        scheduled_at: scheduled.toISOString(),
        schedule_mode: scheduleMode,
      });
      setQuote(result);
    } catch {
      setQuoteError(t("quoteError"));
    } finally {
      setQuoteLoading(false);
    }
  }

  function handleContinueBooking() {
    if (!quote) return;
    router.push(`/book/continue?quote_id=${quote.quote_id}`);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.65, delay: 0.25 }}
      className="w-full"
    >
      <div className="relative rounded-2xl sm:rounded-[1.75rem] md:rounded-[2rem] bg-white/95 backdrop-blur-2xl border border-white/70 shadow-[0_24px_80px_-16px_rgba(10,22,40,0.4)] overflow-hidden">
        {/* Subtle top glow */}
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-secondary/40 to-transparent" />

        {/* Header + tabs */}
        <div className="flex flex-col gap-4 px-4 pt-5 pb-4 sm:px-7 sm:pt-7 md:flex-row md:items-center md:justify-between">
          <div className="min-w-0">
            <h2 className="type-h3 font-bold text-primary tracking-tight">
              {t("title")}
            </h2>
            <p className="mt-1 type-small text-muted line-clamp-2 sm:line-clamp-none">
              {t("subtitle")}
            </p>
          </div>
          <WidgetTabs activeTab={activeTab} setActiveTab={setActiveTab} t={t} />
        </div>

        <div className="px-4 pb-5 space-y-4 sm:px-7 sm:pb-7 sm:space-y-5">
          {/* Main row: addresses + options */}
          <div className="grid md:grid-cols-2 gap-4 md:gap-5">
            {/* Uber-style address route */}
            <div className="relative rounded-2xl bg-gray-bg/80 border border-gray-200/60 p-4 sm:p-5">
              <button
                type="button"
                onClick={swapAddresses}
                aria-label={t("swapAddresses")}
                className="absolute right-2 sm:right-3 top-1/2 -translate-y-1/2 z-10 touch-target w-11 h-11 rounded-full bg-white border border-gray-200/80 flex items-center justify-center text-muted hover:text-secondary hover:border-secondary/40 hover:shadow-md transition-all cursor-pointer"
              >
                <ArrowUpDown className="w-4 h-4" />
              </button>

              <div className="flex gap-3 pr-12 sm:pr-14">
                {/* Route line */}
                <div className="flex flex-col items-center pt-3 pb-3 shrink-0">
                  <div className="booking-icon-badge bg-secondary/15 text-secondary">
                    <Circle className="w-4 h-4 fill-secondary text-secondary" />
                  </div>
                  <div className="w-0.5 flex-1 min-h-[2rem] my-1.5 bg-gradient-to-b from-secondary/50 to-primary/30 rounded-full" />
                  <div className="booking-icon-badge bg-primary/10 text-primary">
                    <MapPin className="w-4 h-4" />
                  </div>
                </div>

                {/* Inputs */}
                <div className="flex-1 flex flex-col gap-3 min-w-0">
                  <div className="group">
                    <label className="type-caption font-bold text-muted mb-1.5 block normal-case">
                      {t("pickupAddress")}
                    </label>
                    <AddressAutocompleteInput
                      id="booking-pickup"
                      value={pickup?.formatted ?? ""}
                      onChange={(value) =>
                        setPickup(value ? { formatted: value } : null)
                      }
                      onPlaceSelect={setPickup}
                      placeholder={t("pickupPlaceholder")}
                    />
                  </div>
                  <div className="group">
                    <label className="type-caption font-bold text-muted mb-1.5 block normal-case">
                      {t("dropoffAddress")}
                    </label>
                    <AddressAutocompleteInput
                      id="booking-dropoff"
                      value={dropoff?.formatted ?? ""}
                      onChange={(value) =>
                        setDropoff(value ? { formatted: value } : null)
                      }
                      onPlaceSelect={setDropoff}
                      placeholder={t("dropoffPlaceholder")}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Schedule + quick options */}
            <div className="flex flex-col gap-4">
              {/* When */}
              <div className="rounded-2xl bg-gray-bg/80 border border-gray-200/60 p-4 sm:p-5">
                <span className="type-caption font-bold text-muted mb-3 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" />
                  {t("schedule")}
                </span>
                <div className="flex flex-col sm:flex-row gap-2 mb-3">
                  <button
                    type="button"
                    onClick={() => setScheduleMode("now")}
                    className={cn(
                      "booking-chip flex-1 justify-center",
                      scheduleMode === "now" ? "booking-chip-active" : "booking-chip-inactive"
                    )}
                  >
                    <Zap className="w-4 h-4" />
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
                    <Calendar className="w-4 h-4" />
                    {t("scheduleLater")}
                  </button>
                </div>
                <AnimatePresence>
                  {scheduleMode === "later" && (
                    <ScheduleDateTimePicker
                      value={scheduledAt}
                      onChange={setScheduledAt}
                    />
                  )}
                </AnimatePresence>
              </div>

              {/* Package quick fields */}
              <div className="rounded-2xl bg-gray-bg/80 border border-gray-200/60 p-4 sm:p-5 flex-1">
                <span className="type-caption font-bold text-muted mb-3 block">
                  {t("packageDetails")}
                </span>
                <div className="flex flex-col sm:flex-row gap-2">
                  <div className="flex items-center gap-2 flex-1 bg-white rounded-full px-4 py-3 border border-gray-200/60 focus-within:border-secondary/40 focus-within:ring-2 focus-within:ring-secondary/15 transition-all">
                    <Scale className="w-4 h-4 text-secondary shrink-0" />
                    <input
                      type="text"
                      placeholder={t("weight")}
                      value={weight}
                      onChange={(e) => setWeight(e.target.value)}
                      className="w-full bg-transparent text-base text-primary placeholder:text-muted/50 outline-none"
                    />
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
            </div>
          </div>

          {/* Delivery type chips */}
          <div>
            <span className="type-caption font-bold text-muted mb-3 flex items-center gap-1.5">
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
                  <Icon className="w-4 h-4" />
                  {t(`deliveryOptions.${key}`)}
                </button>
              ))}
            </div>
          </div>

          {/* Vehicle chips */}
          <div>
            <span className="type-caption font-bold text-muted mb-3 flex items-center gap-1.5">
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
                    selectedVehicle === key
                      ? "booking-chip-active"
                      : "booking-chip-inactive"
                  )}
                >
                  <VehicleIllustration
                    type={resolveVehicleIllustration(key)}
                    id={`chip-${key}`}
                    variant="dark"
                    className="w-[1.2rem] h-[0.6rem] shrink-0 opacity-80"
                  />
                  {t(`vehicleOptions.${key}`)}
                </button>
              ))}
            </div>
          </div>

          {/* CTA — full-width pill button */}
          <Button
            shape="pill"
            size="lg"
            type="button"
            disabled={quoteLoading}
            onClick={handleInstantQuote}
            className="w-full min-h-[3.5rem] sm:min-h-[3.75rem] font-bold text-base gap-3 bg-gradient-to-r from-secondary to-[#1d4ed8] hover:from-[#1d4ed8] hover:to-[#1e40af] shadow-xl shadow-secondary/30 group"
          >
            <span className="flex items-center justify-center w-9 h-9 rounded-full bg-white/20">
              <Sparkles className="w-5 h-5" />
            </span>
            {quoteLoading ? t("quoteLoading") : t("instantQuote")}
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </Button>

          {quoteError && (
            <p className="text-center type-caption text-red-600">{quoteError}</p>
          )}

          {quote && (
            <div className="rounded-2xl bg-secondary/5 border border-secondary/20 p-4 text-center space-y-3">
              <p className="type-body font-bold text-primary">
                {t("quoteResult", { amount: quote.amount_display })}
              </p>
              <p className="type-caption text-muted">
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
            </div>
          )}

          <p className="text-center type-caption normal-case tracking-normal text-muted flex items-center justify-center gap-1">
            <ChevronDown className="w-3 h-3 opacity-50" />
            {t("quoteNote")}
          </p>
        </div>
      </div>
    </motion.div>
  );
}

function WidgetTabs({
  activeTab,
  setActiveTab,
  t,
}: {
  activeTab: (typeof TAB_KEYS)[number];
  setActiveTab: (tab: (typeof TAB_KEYS)[number]) => void;
  t: (key: string) => string;
}) {
  const router = useRouter();

  return (
    <div className="flex w-full sm:w-auto p-1 rounded-full bg-gray-bg border border-gray-200/80 shrink-0">
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
              "relative flex flex-1 sm:flex-none items-center justify-center gap-2 px-4 sm:px-5 py-2.5 min-h-[2.75rem] type-nav-strong rounded-full transition-all cursor-pointer whitespace-nowrap",
              isActive
                ? "bg-white text-secondary font-bold shadow-md shadow-secondary/10"
                : "text-muted hover:text-primary hover:font-bold"
            )}
          >
            <Icon className={cn("w-4 h-4 shrink-0", isActive && "text-secondary")} />
            <span>{t(`tabs.${tab}`)}</span>
          </button>
        );
      })}
    </div>
  );
}
