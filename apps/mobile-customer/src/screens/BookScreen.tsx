import { pickDocuments, uploadAll, type PendingDoc } from "../attachments";
import { DeliveryOptionsField } from "../ui/DeliveryOptionsField";
import { openDocuments } from "../documents";
import { useEffect, useState } from "react";
import {
  InputAccessoryView,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
  StyleSheet,
} from "react-native";
import * as WebBrowser from "expo-web-browser";
import { expiresIn, priceSummary, shortAddress } from "../format";
import { haptic } from "../haptics";
import { radius, spacing, touchTargetMin, useThemed, type Palette } from "../theme";
import {
  Banner,
  Button,
  Card,
  Chip,
  Divider,
  Icon,
  ListRow,
  Progress,
  Segmented,
  StatusPill,
  Txt,
} from "../ui/kit";
import {
  normalizeDeliveryOptions,
  type DeliveryOptions,
  CAPACITY_CLASS_OPTIONS,
  MAX_DROPS,
  bookingText,
  vehicleLabel as capacityVehicleLabel,
} from "@porterchain/types";
import {
  bookingCatalog,
  createQuote,
  formatCad,
  getQuote,
  mockComplete,
  pollCheckout,
  previewQuote,
  rebook,
  startBooking,
  type Address,
  type BookingConfirmation,
  type QuoteResult,
} from "../api";
import { humanCustomerError } from "../errors";
import type { VisitorTracking } from "../linking";
import { sessionIdentity } from "../session";
import { AddressField } from "../ui/AddressField";
import { ConsentCheck } from "../ui/ConsentCheck";
import { DANGEROUS_GOODS, PRIVACY_NOTICE, TERMS_OF_SERVICE } from "../ui/consentCopy";
import {
  addressReady,
  dayChoices,
  dayLabel,
  parseDeclaredCents,
  slotsFor,
  timeLabel,
} from "../ui/bookRules";
import { formatCanadianPhone } from "../ui/canadaPhone";
import { Screen } from "../ui/Screen";
import { SuggestField } from "../ui/SuggestField";

const KEYBOARD_BAR = "pcdc-book-keyboard";

const VALUES = [
  { label: "$100", value: "100" },
  { label: "$500", value: "500" },
  { label: "$1,000", value: "1000" },
  { label: "$5,000", value: "5000" },
];

const INSTRUCTIONS = [
  { label: "Call on arrival", value: "Call on arrival" },
  { label: "Leave at the door", value: "Leave at the door" },
  { label: "Reception", value: "Leave with reception or the front desk" },
  { label: "Buzz code", value: "Buzz code is on the door" },
];

type CatalogVehicle = {
  id: string;
  label: string;
  allowed_presets?: string[] | null;
  whole_vehicle_enabled?: boolean;
  capacity_kg?: number | null;
  max_length_cm?: number | null;
  max_width_cm?: number | null;
  max_height_cm?: number | null;
};

type CatalogPreset = {
  id: string;
  label: string;
  manual?: boolean;
  length_in?: number | null;
  width_in?: number | null;
  height_in?: number | null;
  weight_lb?: number | null;
};

const VEHICLES: CatalogVehicle[] = CAPACITY_CLASS_OPTIONS.map((row) => ({
  id: row.id,
  label: row.label,
}));

const PRESETS: CatalogPreset[] = [
  { id: "small", label: "Small" },
  { id: "medium", label: "Medium" },
  { id: "large", label: "Large" },
  { id: "extra_large", label: "Extra large" },
  { id: "skid", label: "Skid" },
  { id: "furniture", label: "Furniture" },
  { id: "other", label: "Other" },
];

const VEHICLE_ALIAS: Record<string, string> = {
  sedan: "sedan_suv",
  suv: "sedan_suv",
  cargoVan: "cargo_van",
  box16: "box_16",
  box20: "box_20",
  box_truck: "box_16",
  highRoof: "sprinter_van",
  highroof: "sprinter_van",
};

type BookStep = "details" | "quote" | "pay" | "done";

type ParcelRow = {
  preset_id: string;
  instructions: string;
  length_in: string;
  width_in: string;
  height_in: string;
  weight_lb: string;
};

function blankRow(presetId = "small"): ParcelRow {
  return {
    preset_id: presetId,
    instructions: "",
    length_in: "",
    width_in: "",
    height_in: "",
    weight_lb: "",
  };
}

function pieceFits(
  vehicle: CatalogVehicle,
  row: ParcelRow,
  preset: CatalogPreset | undefined
): boolean {
  if (vehicle.allowed_presets?.length && !vehicle.allowed_presets.includes(row.preset_id))
    return false;
  const manual = preset?.manual || row.preset_id === "other";
  const length = (manual ? Number(row.length_in) : Number(preset?.length_in)) * 2.54;
  const width = (manual ? Number(row.width_in) : Number(preset?.width_in)) * 2.54;
  const height = (manual ? Number(row.height_in) : Number(preset?.height_in)) * 2.54;
  const weight = (manual ? Number(row.weight_lb) : Number(preset?.weight_lb)) * 0.45359237;
  if (![length, width, height, weight].every((n) => Number.isFinite(n) && n > 0)) return true;
  const dims = [length, width, height].sort((a, b) => b - a);
  const limits = [vehicle.max_length_cm, vehicle.max_width_cm, vehicle.max_height_cm]
    .map((n) => Number(n))
    .filter((n) => Number.isFinite(n) && n > 0)
    .sort((a, b) => b - a);
  if (limits.length === 3 && dims.some((side, index) => side > limits[index]!)) return false;
  if (vehicle.capacity_kg && weight > Number(vehicle.capacity_kg)) return false;
  return true;
}

function rowsFromSaved(
  items: Array<{
    preset_id?: string;
    instructions?: string | null;
    length_cm?: number;
    width_cm?: number;
    height_cm?: number;
    weight_kg?: number;
  }>
): ParcelRow[] {
  return items.map((parcel) => ({
    preset_id: parcel.preset_id || "small",
    instructions: parcel.instructions || "",
    length_in: parcel.length_cm ? String(Math.round((parcel.length_cm / 2.54) * 10) / 10) : "",
    width_in: parcel.width_cm ? String(Math.round((parcel.width_cm / 2.54) * 10) / 10) : "",
    height_in: parcel.height_cm ? String(Math.round((parcel.height_cm / 2.54) * 10) / 10) : "",
    weight_lb: parcel.weight_kg
      ? String(Math.round((parcel.weight_kg / 0.45359237) * 10) / 10)
      : "",
  }));
}

function emptyAddress(): Address {
  return { formatted: "" };
}

type Props = {
  rebookOrderId?: string;
  quoteId?: string;
  vehicle?: string;
  visitorId?: string;
  visitorTracking?: VisitorTracking;
  onTracked: (tracking: string) => void;
};

export function BookScreen({
  rebookOrderId,
  quoteId,
  vehicle,
  visitorId,
  visitorTracking,
  onTracked,
}: Props) {
  const [vehicles, setVehicles] = useState(VEHICLES);
  const [presets, setPresets] = useState(PRESETS);
  const [includedKm, setIncludedKm] = useState<number | null>(null);
  const [vehicleClass, setVehicleClass] = useState(
    VEHICLE_ALIAS[vehicle ?? ""] ?? vehicle ?? "sedan_suv"
  );
  const [bookingMode, setBookingMode] = useState<"parcels" | "vehicle">("parcels");
  const [rows, setRows] = useState<ParcelRow[]>([blankRow()]);
  const [activeParcel, setActiveParcel] = useState(0);
  const [liveFare, setLiveFare] = useState<{ amount: string; km: number | null } | null>(null);
  const [pickup, setPickup] = useState<Address>(emptyAddress());
  const [dropoff, setDropoff] = useState<Address>(emptyAddress());
  // Shared rule (@porterchain/types booking): up to MAX_DROPS drops = drop-off + extra stops.
  const [extraStops, setExtraStops] = useState<Address[]>([]);
  const [pickupManual, setPickupManual] = useState(false);
  const [dropoffManual, setDropoffManual] = useState(false);
  const [stopManual, setStopManual] = useState(false);
  const [declared, setDeclared] = useState("");
  const [instructions, setInstructions] = useState("");
  const [dlv, setDlv] = useState<DeliveryOptions>({});
  const [promo, setPromo] = useState("");
  const [phone, setPhone] = useState("");
  const [later, setLater] = useState(false);
  const [dayIndex, setDayIndex] = useState(0);
  const [slot, setSlot] = useState<string | null>(null);
  const [step, setStep] = useState<BookStep>("details");
  const [terms, setTerms] = useState(false);
  const [privacy, setPrivacy] = useState(false);
  const [dangerous, setDangerous] = useState(false);
  const [quote, setQuote] = useState<QuoteResult | null>(null);
  const [done, setDone] = useState<BookingConfirmation | null>(null);
  const [busy, setBusy] = useState(false);
  const [docs, setDocs] = useState<PendingDoc[]>([]);
  const [docNote, setDocNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [moreOpen, setMoreOpen] = useState(false);
  const { colors, styles } = useThemed(makeStyles);

  useEffect(() => {
    const mapped = vehicle ? (VEHICLE_ALIAS[vehicle] ?? vehicle) : "";
    if (mapped && vehicles.some((row) => row.id === mapped)) setVehicleClass(mapped);
  }, [vehicle, vehicles]);

  useEffect(() => {
    let cancelled = false;
    bookingCatalog()
      .then((catalog) => {
        if (cancelled) return;
        if (catalog.vehicles?.length) {
          setVehicles(
            catalog.vehicles.map((row) => ({
              id: row.id,
              label: row.label,
              allowed_presets: row.allowed_presets,
              whole_vehicle_enabled: row.whole_vehicle_enabled,
              capacity_kg: row.capacity_kg,
              max_length_cm: row.max_length_cm,
              max_width_cm: row.max_width_cm,
              max_height_cm: row.max_height_cm,
            }))
          );
        }
        if (catalog.presets?.length) setPresets(catalog.presets);
        if (catalog.included_km) setIncludedKm(catalog.included_km);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!rebookOrderId) return;
    void rebook(rebookOrderId)
      .then((payload) => {
        setPickup(payload.pickup);
        setDropoff(payload.dropoff);
        if (payload.vehicle_class)
          setVehicleClass(VEHICLE_ALIAS[payload.vehicle_class] ?? payload.vehicle_class);
        if (payload.booking_mode === "vehicle" || payload.booking_mode === "parcels")
          setBookingMode(payload.booking_mode);
        if (payload.parcels?.length) setRows(rowsFromSaved(payload.parcels));
        setExtraStops(
          (payload.additional_stops ?? []).filter((x) => x?.formatted).slice(0, MAX_DROPS - 1)
        );
        if (payload.declared_value_cents)
          setDeclared((payload.declared_value_cents / 100).toFixed(2));
      })
      .catch((err: unknown) => {
        setError(humanCustomerError(err instanceof Error ? err.message : "request_failed"));
      });
  }, [rebookOrderId]);

  useEffect(() => {
    if (!quoteId) return;
    let cancelled = false;
    void getQuote(quoteId)
      .then((resumed) => {
        if (cancelled) return;
        if (resumed.pickup?.formatted) setPickup(resumed.pickup);
        if (resumed.dropoff?.formatted) setDropoff(resumed.dropoff);
        if (resumed.vehicle_class)
          setVehicleClass(VEHICLE_ALIAS[resumed.vehicle_class] ?? resumed.vehicle_class);
        if (resumed.booking_mode === "vehicle" || resumed.booking_mode === "parcels")
          setBookingMode(resumed.booking_mode);
        if (resumed.parcels?.length) setRows(rowsFromSaved(resumed.parcels));
        setExtraStops(
          (resumed.additional_stops ?? []).filter((x) => x?.formatted).slice(0, MAX_DROPS - 1)
        );
        if (resumed.declared_value_cents)
          setDeclared((resumed.declared_value_cents / 100).toFixed(2));
        setQuote(resumed);
        setStep("quote");
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(humanCustomerError(err instanceof Error ? err.message : "request_failed"));
      });
    return () => {
      cancelled = true;
    };
  }, [quoteId]);

  function quoteBody() {
    return {
      pickup,
      dropoff: { ...dropoff, delivery_options: normalizeDeliveryOptions(dlv) },
      vehicle_class: vehicleClass,
      booking_mode: bookingMode,
      parcels:
        bookingMode === "vehicle"
          ? undefined
          : rows.map((row) => ({
              preset_id: row.preset_id,
              quantity: 1,
              instructions: row.instructions.trim() || undefined,
              length_in: row.length_in ? Number(row.length_in) : undefined,
              width_in: row.width_in ? Number(row.width_in) : undefined,
              height_in: row.height_in ? Number(row.height_in) : undefined,
              weight_lb: row.weight_lb ? Number(row.weight_lb) : undefined,
            })),
      declared_value_cents: parseDeclaredCents(declared),
      additional_stops: extraStops.some((x) => x.formatted.trim())
        ? extraStops.filter((x) => x.formatted.trim()).slice(0, MAX_DROPS - 1)
        : undefined,
      special_instructions: instructions.trim() || undefined,
      promo_code: promo.trim() || undefined,
      scheduled_at: later && slot ? slot : new Date(Date.now() + 30 * 60_000).toISOString(),
      schedule_mode: later ? ("later" as const) : ("now" as const),
      anonymous_session_id: visitorId,
      visitor_session_id: visitorId,
      tracking: { ...visitorTracking, device: Platform.OS === "android" ? "android" : "ios" },
    };
  }

  useEffect(() => {
    if (step !== "details" || !addressReady(pickup) || !addressReady(dropoff)) {
      setLiveFare(null);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      previewQuote(quoteBody())
        .then((fare) => {
          if (!cancelled)
            setLiveFare({ amount: fare.amount_display, km: fare.distance_km ?? null });
        })
        .catch(() => {
          if (!cancelled) setLiveFare(null);
        });
    }, 450);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [
    pickup,
    dropoff,
    extraStops,
    vehicleClass,
    bookingMode,
    rows,
    declared,
    promo,
    later,
    slot,
    step,
    instructions,
  ]);

  async function onQuote() {
    if (!addressReady(pickup)) {
      setError(
        pickupManual
          ? "Google could not match the pickup, so a price cannot be calculated yet."
          : "Choose the pickup address from the Google suggestions."
      );
      return;
    }
    if (!addressReady(dropoff)) {
      setError(
        dropoffManual
          ? "Google could not match the drop-off, so a price cannot be calculated yet."
          : "Choose the drop-off address from the Google suggestions."
      );
      return;
    }
    if (extraStops.some((x) => x.formatted.trim() && !addressReady(x))) {
      setError(
        stopManual
          ? "Google could not match the extra stop. Clear it or choose a suggestion."
          : "Choose the extra stop from the Google suggestions, or clear it."
      );
      return;
    }
    if (later && !slot) {
      setError("Pick a pickup time between 6:00 and 22:00.");
      return;
    }
    setBusy(true);
    setError(null);
    setDone(null);
    try {
      const result = await createQuote(quoteBody());
      setQuote(result);
      setStep("quote");
    } catch (err) {
      const raw = err instanceof Error ? err.message : "request_failed";
      if (raw === "vehicle_class_not_available") {
        setVehicles((rows) => rows.filter((row) => row.id !== vehicleClass));
        const next = vehicles.find((row) => row.id !== vehicleClass);
        if (next) setVehicleClass(next.id);
      }
      setError(humanCustomerError(raw));
    } finally {
      setBusy(false);
    }
  }

  async function onPay() {
    if (!quote) return;
    if (!terms || !privacy || !dangerous) {
      setError("Accept the terms, privacy, and dangerous-goods statements.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const identity = sessionIdentity();
      const booking = await startBooking({
        quote_id: quote.quote_id,
        email: identity.email,
        phone: phone.trim(),
        clerk_user_id: identity.userId,
        terms_accepted: terms,
        privacy_accepted: privacy,
        dangerous_goods_confirmed: dangerous,
        consent_at: new Date().toISOString(),
        anonymous_session_id: visitorId,
      });
      let confirmed: BookingConfirmation;
      if (booking.mock_checkout) {
        confirmed = await mockComplete(quote.quote_id);
      } else {
        if (!booking.checkout_url) throw new Error("checkout_unavailable");
        await WebBrowser.openBrowserAsync(booking.checkout_url);
        confirmed = await pollCheckout(quote.quote_id);
      }
      if (docs.length) {
        // Booking exists only once paid; documents attach to it now.
        const failed = await uploadAll(confirmed.tracking_number, docs);
        setDocNote(
          failed.length
            ? `Couldn't attach ${failed.join(", ")}. Tap below to add it again.`
            : `${docs.length} document${docs.length > 1 ? "s" : ""} attached for the driver.`
        );
        if (!failed.length) setDocs([]);
      }
      setDone(confirmed);
      setStep("done");
      haptic.success();
    } catch (err) {
      const raw = err instanceof Error ? err.message : "request_failed";
      setError(humanCustomerError(raw));
      haptic.error();
    } finally {
      setBusy(false);
    }
  }

  const days = dayChoices();
  const slots = slotsFor(days[dayIndex] ?? days[0]!);
  const selectedVehicle = vehicles.find((row) => row.id === vehicleClass);
  const wholeVehicleOk = selectedVehicle?.whole_vehicle_enabled !== false;
  const nextVehicle =
    bookingMode === "parcels" && selectedVehicle
      ? vehicles.find(
          (row) =>
            row.id !== selectedVehicle.id &&
            rows.every((parcel) =>
              pieceFits(
                row,
                parcel,
                presets.find((item) => item.id === parcel.preset_id)
              )
            ) &&
            rows.some(
              (parcel) =>
                !pieceFits(
                  selectedVehicle,
                  parcel,
                  presets.find((item) => item.id === parcel.preset_id)
                )
            )
        )
      : undefined;

  function changeRows(updater: (current: ParcelRow[]) => ParcelRow[]) {
    setRows(updater);
    setQuote(null);
  }

  function vehicleName(id?: string | null) {
    if (!id) return "";
    return vehicles.find((row) => row.id === id)?.label ?? capacityVehicleLabel(id, id);
  }

  useEffect(() => {
    if (!wholeVehicleOk && bookingMode === "vehicle") {
      setBookingMode("parcels");
      setQuote(null);
    }
  }, [wholeVehicleOk, bookingMode]);

  const priced = quote ? priceSummary(quote.pricing_breakdown, quote.amount_cents) : null;
  const total = quote ? quote.amount_display || formatCad(quote.amount_cents) : "";
  const stepIndex = step === "details" ? 0 : step === "quote" ? 1 : 2;
  const setRow = (patch: Partial<ParcelRow>) =>
    changeRows((current) =>
      current.map((row, index) => (index === activeParcel ? { ...row, ...patch } : row))
    );
  const allowedPresets = presets.filter((item) => {
    const allowed = selectedVehicle?.allowed_presets;
    if (allowed?.length) return allowed.includes(item.id);
    return vehicleClass !== "sedan_suv" || ["small", "medium", "large", "other"].includes(item.id);
  });

  const footer =
    step === "done" ? null : step === "details" ? (
      <>
        <View style={styles.fareRow}>
          <Txt v="callout" tone="muted">
            {liveFare ? "Estimated price" : "Add both addresses for a price"}
          </Txt>
          {liveFare ? (
            <Txt v="title" accessibilityLabel={`Estimated price ${liveFare.amount}`}>
              {liveFare.amount.replace(" CAD", "")}
            </Txt>
          ) : null}
        </View>
        <Button
          testID="book-get-quote"
          label="Review price"
          loading={busy}
          onPress={() => void onQuote()}
        />
      </>
    ) : step === "quote" ? (
      <Button testID="book-continue" label="Continue" onPress={() => setStep("pay")} />
    ) : (
      <>
        <Button
          testID="book-pay"
          icon="card"
          label={`Pay ${total.replace(" CAD", "")} by card`}
          loading={busy}
          disabled={!terms || !privacy || !dangerous}
          onPress={() => void onPay()}
        />
        <View style={styles.secure}>
          <Icon name="lock-closed" size={13} color={colors.muted} />
          <Txt v="caption" tone="muted">
            Secure card checkout by Stripe · Apple Pay and Google Pay accepted
          </Txt>
        </View>
      </>
    );

  return (
    <Screen footer={footer}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={Platform.OS === "ios" ? 140 : 0}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardDismissMode="interactive"
          keyboardShouldPersistTaps="handled"
          testID="book"
        >
          {step === "done" && done ? (
            <View style={styles.doneWrap} testID="book-done">
              <View style={[styles.doneIcon, { backgroundColor: colors.successBg }]}>
                <Icon name="checkmark" size={44} color={colors.success} />
              </View>
              <Txt v="largeTitle" center accessibilityRole="header">
                You're booked
              </Txt>
              <Txt v="body" tone="muted" center>
                We'll notify you when a driver is assigned. A receipt is on its way by email.
              </Txt>
              <Card style={{ alignSelf: "stretch" }}>
                <Txt v="overline" tone="muted">
                  Tracking number
                </Txt>
                <Txt v="title" selectable>
                  {done.tracking_number}
                </Txt>
                <Txt v="callout" tone="muted">
                  {done.booking_mode === "vehicle"
                    ? "Whole vehicle"
                    : done.parcels
                        ?.map((item) => item.preset_label)
                        .filter(Boolean)
                        .join(", ") || `${done.parcels?.length || 0} parcels`}
                  {done.vehicle_class ? ` · ${vehicleName(done.vehicle_class)}` : ""}
                  {done.invoice_number ? ` · Invoice ${done.invoice_number}` : ""}
                  {` · ${formatCad(done.amount_cents, done.currency)} paid`}
                </Txt>
              </Card>
              {docNote ? <Banner tone="info" text={docNote} /> : null}
              <Button
                icon="locate"
                label="Track shipment"
                onPress={() => onTracked(done.tracking_number)}
              />
              <Button
                testID="book-attach-docs"
                variant="ghost"
                icon="document-attach-outline"
                label={docNote ? "Manage pickup documents" : "Attach a pickup document"}
                onPress={() => void openDocuments(done.tracking_number)}
              />
            </View>
          ) : (
            <>
              <View style={styles.headerRow}>
                {step !== "details" ? (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="Back"
                    hitSlop={8}
                    onPress={() => {
                      if (step === "pay") setStep("quote");
                      else {
                        setQuote(null);
                        setStep("details");
                      }
                    }}
                    style={styles.back}
                  >
                    <Icon name="chevron-back" size={24} color={colors.accentText} />
                  </Pressable>
                ) : null}
                <Txt v="largeTitle" accessibilityRole="header" style={{ flex: 1 }}>
                  {step === "details"
                    ? "Book delivery"
                    : step === "quote"
                      ? "Review price"
                      : "Confirm & pay"}
                </Txt>
              </View>
              <Progress steps={["Details", "Review", "Pay"]} current={stepIndex} />
              <Txt v="caption" tone="muted">
                Step {stepIndex + 1} of 3 ·{" "}
                {["Addresses and load", "Price with HST", "Card payment"][stepIndex]}
              </Txt>
              {error ? <Banner tone="danger" text={error} /> : null}

              {step === "details" ? (
                <>
                  <Card>
                    <Txt v="headline" accessibilityRole="header">
                      Where
                    </Txt>
                    <AddressField
                      label="Pickup"
                      value={pickup}
                      onChange={(next) => {
                        setPickup(next);
                        setQuote(null);
                      }}
                      accessoryId={KEYBOARD_BAR}
                      onManualOk={setPickupManual}
                    />
                    <AddressField
                      label="Drop-off"
                      value={dropoff}
                      onChange={(next) => {
                        setDropoff(next);
                        setQuote(null);
                      }}
                      accessoryId={KEYBOARD_BAR}
                      onManualOk={setDropoffManual}
                    />
                    {extraStops.map((stop, i) => (
                      <AddressField
                        key={i}
                        label={`${bookingText("en", "dropN", { n: i + 1 })} (before final drop-off)`}
                        value={stop}
                        onChange={(next) => {
                          setExtraStops((all) => all.map((x, j) => (j === i ? next : x)));
                          setQuote(null);
                        }}
                        accessoryId={KEYBOARD_BAR}
                        onManualOk={setStopManual}
                      />
                    ))}
                    {extraStops.length < MAX_DROPS - 1 ? (
                      <Button
                        variant="plain"
                        compact
                        icon="add-circle-outline"
                        label={`${bookingText("en", "addDrop")} (${extraStops.length + 1}/${MAX_DROPS})`}
                        onPress={() => setExtraStops((all) => [...all, emptyAddress()])}
                        style={{ alignSelf: "flex-start", paddingHorizontal: 0 }}
                      />
                    ) : (
                      <Txt v="caption" tone="muted">
                        {bookingText("en", "dropsLimit")}
                      </Txt>
                    )}
                  </Card>

                  <Card>
                    <Txt v="headline" accessibilityRole="header">
                      When
                    </Txt>
                    <View style={styles.chips}>
                      <Chip
                        icon="flash-outline"
                        label="As soon as possible"
                        selected={!later}
                        onPress={() => {
                          setLater(false);
                          setSlot(null);
                          setQuote(null);
                        }}
                      />
                      <Chip
                        icon="calendar-outline"
                        label="Schedule"
                        selected={later}
                        onPress={() => {
                          setLater(true);
                          setQuote(null);
                        }}
                      />
                    </View>
                    {later ? (
                      <>
                        <ScrollView
                          horizontal
                          showsHorizontalScrollIndicator={false}
                          contentContainerStyle={styles.chipsRow}
                        >
                          {days.map((day, index) => (
                            <Chip
                              key={day.toISOString()}
                              label={dayLabel(day)}
                              selected={index === dayIndex}
                              onPress={() => {
                                setDayIndex(index);
                                setSlot(null);
                                setQuote(null);
                              }}
                            />
                          ))}
                        </ScrollView>
                        <View style={styles.chips}>
                          {slots.length ? (
                            slots.map((iso) => (
                              <Chip
                                key={iso}
                                label={timeLabel(iso)}
                                selected={iso === slot}
                                onPress={() => {
                                  setSlot(iso);
                                  setQuote(null);
                                }}
                              />
                            ))
                          ) : (
                            <Txt v="callout" tone="muted">
                              No times left today. Pick another day.
                            </Txt>
                          )}
                        </View>
                      </>
                    ) : null}
                  </Card>

                  <Card>
                    <Txt v="headline" accessibilityRole="header">
                      Vehicle
                    </Txt>
                    <ScrollView
                      horizontal
                      showsHorizontalScrollIndicator={false}
                      contentContainerStyle={styles.chipsRow}
                    >
                      {vehicles.map((item) => (
                        <Chip
                          key={item.id}
                          icon={
                            item.id.startsWith("box")
                              ? "bus-outline"
                              : item.id.includes("van")
                                ? "car-sport-outline"
                                : "car-outline"
                          }
                          label={item.label}
                          selected={item.id === vehicleClass}
                          onPress={() => {
                            setVehicleClass(item.id);
                            setQuote(null);
                          }}
                        />
                      ))}
                    </ScrollView>
                    {includedKm ? (
                      <Txt v="caption" tone="muted">
                        Price includes the first {includedKm} km, then per km.
                      </Txt>
                    ) : null}
                    {wholeVehicleOk ? (
                      <Segmented
                        options={[
                          { id: "parcels", label: "Parcels" },
                          { id: "vehicle", label: "Whole vehicle" },
                        ]}
                        value={bookingMode}
                        onChange={(id) => {
                          setBookingMode(id);
                          setQuote(null);
                        }}
                      />
                    ) : null}
                    {nextVehicle ? (
                      <Banner
                        tone="warning"
                        text={`This load needs a ${nextVehicle.label}.`}
                        action="Switch"
                        onAction={() => {
                          setVehicleClass(nextVehicle.id);
                          setQuote(null);
                        }}
                      />
                    ) : null}
                  </Card>

                  {bookingMode === "parcels" ? (
                    <Card>
                      <View style={styles.rowBetween}>
                        <Txt v="headline" accessibilityRole="header">
                          Parcels
                        </Txt>
                        <Txt v="caption" tone="muted">
                          {rows.length} item{rows.length > 1 ? "s" : ""}
                        </Txt>
                      </View>
                      {rows.length > 1 ? (
                        <ScrollView
                          horizontal
                          showsHorizontalScrollIndicator={false}
                          contentContainerStyle={styles.chipsRow}
                        >
                          {rows.map((row, index) => (
                            <Chip
                              key={`${row.preset_id}-${index}`}
                              label={`${index + 1}. ${presets.find((item) => item.id === row.preset_id)?.label || row.preset_id}`}
                              selected={index === activeParcel}
                              onPress={() => setActiveParcel(index)}
                            />
                          ))}
                        </ScrollView>
                      ) : null}
                      <Txt v="caption" tone="muted">
                        Size{rows.length > 1 ? ` for parcel ${activeParcel + 1}` : ""}
                      </Txt>
                      <View style={styles.chips}>
                        {allowedPresets.map((item) => (
                          <Chip
                            key={item.id}
                            label={item.label}
                            selected={rows[activeParcel]?.preset_id === item.id}
                            onPress={() => setRow({ preset_id: item.id })}
                          />
                        ))}
                      </View>
                      {rows[activeParcel]?.preset_id === "other" ? (
                        <View style={styles.dims}>
                          {(
                            [
                              ["length_in", "Length", "in"],
                              ["width_in", "Width", "in"],
                              ["height_in", "Height", "in"],
                              ["weight_lb", "Weight", "lb"],
                            ] as const
                          ).map(([key, label, unit]) => (
                            <View key={key} style={styles.dim}>
                              <Txt v="caption" tone="muted">
                                {label} ({unit})
                              </Txt>
                              <TextInput
                                accessibilityLabel={`${label} in ${unit === "in" ? "inches" : "pounds"}`}
                                style={styles.input}
                                keyboardType="decimal-pad"
                                value={rows[activeParcel]?.[key] ?? ""}
                                onChangeText={(value) =>
                                  setRow({ [key]: value } as Partial<ParcelRow>)
                                }
                                placeholder="0"
                                placeholderTextColor={colors.muted}
                                inputAccessoryViewID={KEYBOARD_BAR}
                                maxFontSizeMultiplier={1.6}
                              />
                            </View>
                          ))}
                        </View>
                      ) : null}
                      <SuggestField
                        label="Note for this parcel"
                        value={rows[activeParcel]?.instructions ?? ""}
                        onChange={(value) => setRow({ instructions: value })}
                        placeholder="Optional"
                        suggestions={INSTRUCTIONS}
                        accessoryId={KEYBOARD_BAR}
                      />
                      <View style={styles.chips}>
                        <Button
                          variant="ghost"
                          compact
                          icon="add"
                          label="Add parcel"
                          onPress={() => {
                            changeRows((current) => [...current, blankRow()]);
                            setActiveParcel(rows.length);
                          }}
                        />
                        {rows.length > 1 ? (
                          <Button
                            variant="plain"
                            compact
                            icon="trash-outline"
                            label="Remove"
                            onPress={() => {
                              changeRows((current) =>
                                current.filter((_, index) => index !== activeParcel)
                              );
                              setActiveParcel((current) => Math.max(0, current - 1));
                            }}
                          />
                        ) : null}
                      </View>
                    </Card>
                  ) : null}

                  <Card>
                    <Txt v="headline" accessibilityRole="header">
                      Contact on the day
                    </Txt>
                    <TextInput
                      style={styles.input}
                      accessibilityLabel="Phone for the driver"
                      placeholder="Phone, +1 xxx-xxx-xxxx"
                      keyboardType="phone-pad"
                      textContentType="telephoneNumber"
                      autoComplete="tel"
                      value={phone}
                      onChangeText={(text) => setPhone(formatCanadianPhone(text))}
                      placeholderTextColor={colors.muted}
                      inputAccessoryViewID={KEYBOARD_BAR}
                      maxFontSizeMultiplier={1.6}
                    />
                    <SuggestField
                      label="Instructions for the driver"
                      value={instructions}
                      onChange={setInstructions}
                      placeholder="Optional"
                      suggestions={INSTRUCTIONS}
                      accessoryId={KEYBOARD_BAR}
                    />
                    <DeliveryOptionsField
                      value={dlv}
                      onChange={setDlv}
                      accessoryId={KEYBOARD_BAR}
                    />
                  </Card>

                  <Card>
                    <Pressable
                      accessibilityRole="button"
                      accessibilityState={{ expanded: moreOpen }}
                      onPress={() => setMoreOpen((v) => !v)}
                      style={styles.rowBetween}
                    >
                      <View style={{ flex: 1 }}>
                        <Txt v="headline">More options</Txt>
                        <Txt v="caption" tone="muted">
                          Declared value, promo code
                          {declared || promo ? " · added" : ""}
                        </Txt>
                      </View>
                      <Icon
                        name={moreOpen ? "chevron-up" : "chevron-down"}
                        size={20}
                        color={colors.muted}
                      />
                    </Pressable>
                    {moreOpen ? (
                      <>
                        <SuggestField
                          label="Declared value (CAD)"
                          value={declared}
                          onChange={(value) => {
                            setDeclared(value);
                            setQuote(null);
                          }}
                          placeholder="Dollars, or pick one"
                          suggestions={VALUES}
                          keyboardType="decimal-pad"
                          accessoryId={KEYBOARD_BAR}
                        />
                        <TextInput
                          style={styles.input}
                          accessibilityLabel="Promo code"
                          placeholder="Promo code"
                          autoCapitalize="characters"
                          value={promo}
                          onChangeText={(text) => {
                            setPromo(text);
                            setQuote(null);
                          }}
                          placeholderTextColor={colors.muted}
                          inputAccessoryViewID={KEYBOARD_BAR}
                          maxFontSizeMultiplier={1.6}
                        />
                      </>
                    ) : null}
                  </Card>
                </>
              ) : null}

              {step === "quote" && quote && priced ? (
                <>
                  <Card style={{ gap: 0, paddingVertical: spacing.xs }}>
                    <ListRow
                      icon="arrow-up-circle"
                      title={shortAddress(pickup.formatted)}
                      subtitle={pickup.formatted}
                    />
                    <Divider />
                    {extraStops
                      .filter((x) => x.formatted.trim())
                      .map((x, i) => (
                        <View key={i}>
                          <ListRow
                            icon="ellipse-outline"
                            title={shortAddress(x.formatted)}
                            subtitle="Extra stop"
                          />
                          <Divider />
                        </View>
                      ))}
                    <ListRow
                      icon="flag"
                      title={shortAddress(dropoff.formatted)}
                      subtitle={dropoff.formatted}
                    />
                    <Divider />
                    <ListRow
                      icon="time-outline"
                      title={
                        later && slot
                          ? `${dayLabel(new Date(slot))} · ${timeLabel(slot)}`
                          : "As soon as possible"
                      }
                      subtitle={[
                        vehicleName(quote.vehicle_class),
                        quote.booking_mode === "vehicle"
                          ? "Whole vehicle"
                          : `${rows.length} parcel${rows.length > 1 ? "s" : ""}`,
                        quote.distance_km != null ? `${quote.distance_km} km` : "",
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    />
                  </Card>
                  <Card testID="book-price">
                    <Txt v="headline" accessibilityRole="header">
                      Price
                    </Txt>
                    {priced.lines.map((line) => (
                      <View key={line.code} style={styles.rowBetween}>
                        <Txt v="callout" tone="muted" style={{ flex: 1 }}>
                          {line.label}
                        </Txt>
                        <Txt v="callout">{formatCad(line.amount_cents)}</Txt>
                      </View>
                    ))}
                    {priced.tax.map((line) => (
                      <View key={line.code} style={styles.rowBetween}>
                        <Txt v="callout" tone="muted" style={{ flex: 1 }}>
                          {line.label}
                        </Txt>
                        <Txt v="callout">{formatCad(line.amount_cents)}</Txt>
                      </View>
                    ))}
                    <Divider />
                    <View style={styles.rowBetween}>
                      <Txt v="headline">Total</Txt>
                      <Txt v="title" accessibilityLabel={`Total ${total}`}>
                        {total}
                      </Txt>
                    </View>
                    <Txt v="caption" tone="muted">
                      {priced.taxItemised ? "HST shown above." : "Total includes 13% HST."}{" "}
                      {expiresIn(quote.expires_at)}.
                    </Txt>
                  </Card>
                </>
              ) : null}

              {step === "pay" && quote ? (
                <>
                  <Card style={styles.rowBetween}>
                    <View>
                      <Txt v="caption" tone="muted">
                        Total incl. HST
                      </Txt>
                      <Txt v="title">{total}</Txt>
                    </View>
                    <Txt v="caption" tone="muted" style={{ textAlign: "right", flexShrink: 1 }}>
                      {shortAddress(pickup.formatted)} → {shortAddress(dropoff.formatted)}
                    </Txt>
                  </Card>
                  <Card testID="book-docs">
                    <Txt v="headline" accessibilityRole="header">
                      Pickup documents
                    </Txt>
                    <Txt v="caption" tone="muted">
                      Optional. For example a warehouse release. Your driver sees them and shows
                      required ones at pickup.
                    </Txt>
                    {docs.map((d, i) => (
                      <View key={`${d.uri}-${i}`} style={styles.docRow}>
                        <Icon
                          name={
                            d.mimeType === "application/pdf"
                              ? "document-text-outline"
                              : "image-outline"
                          }
                          size={20}
                          color={colors.accentText}
                        />
                        <Txt v="callout" numberOfLines={1} style={{ flex: 1 }}>
                          {d.name}
                        </Txt>
                        <Pressable
                          accessibilityRole="switch"
                          accessibilityLabel={`${d.name}: must show at pickup`}
                          accessibilityState={{ checked: d.required }}
                          hitSlop={8}
                          style={styles.tapMin}
                          onPress={() =>
                            setDocs((xs) =>
                              xs.map((x, j) => (j === i ? { ...x, required: !x.required } : x))
                            )
                          }
                        >
                          <StatusPill
                            label={d.required ? "Must show" : "For info"}
                            tone={d.required ? "progress" : "neutral"}
                          />
                        </Pressable>
                        <Pressable
                          accessibilityRole="button"
                          accessibilityLabel={`Remove ${d.name}`}
                          hitSlop={8}
                          style={styles.tapMin}
                          onPress={() => setDocs((xs) => xs.filter((_, j) => j !== i))}
                        >
                          <Icon name="close-circle" size={22} color={colors.muted} />
                        </Pressable>
                      </View>
                    ))}
                    <Button
                      testID="book-add-doc"
                      variant="ghost"
                      compact
                      icon="attach"
                      label="Attach PDF or photo"
                      disabled={busy}
                      onPress={() =>
                        void pickDocuments(docs).then((r) => {
                          setDocs(r.docs);
                          setError(r.error);
                        })
                      }
                    />
                  </Card>
                  <Card>
                    <Txt v="headline" accessibilityRole="header">
                      Before you pay
                    </Txt>
                    <Txt v="caption" tone="muted">
                      Tap a statement to read it, then accept.
                    </Txt>
                    <ConsentCheck
                      label="I accept the Terms of Service"
                      checked={terms}
                      document={TERMS_OF_SERVICE}
                      onChange={setTerms}
                    />
                    <ConsentCheck
                      label="I accept the Privacy Notice"
                      checked={privacy}
                      document={PRIVACY_NOTICE}
                      onChange={setPrivacy}
                    />
                    <ConsentCheck
                      label="No undeclared dangerous goods"
                      checked={dangerous}
                      document={DANGEROUS_GOODS}
                      onChange={setDangerous}
                    />
                  </Card>
                </>
              ) : null}
            </>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
      {Platform.OS === "ios" ? (
        <InputAccessoryView nativeID={KEYBOARD_BAR}>
          <View style={styles.keyboardBar}>
            <Pressable
              accessibilityRole="button"
              onPress={() => Keyboard.dismiss()}
              hitSlop={8}
              style={styles.tapMin}
            >
              <Txt v="headline" tone="accent">
                Done
              </Txt>
            </Pressable>
          </View>
        </InputAccessoryView>
      ) : null}
    </Screen>
  );
}

const makeStyles = (c: Palette) =>
  StyleSheet.create({
    flex: { flex: 1 },
    scroll: { gap: spacing.md, paddingBottom: spacing["2xl"], paddingTop: spacing.xs },
    headerRow: { flexDirection: "row", alignItems: "center", gap: spacing.xs },
    back: {
      minWidth: touchTargetMin,
      minHeight: touchTargetMin,
      justifyContent: "center",
      marginLeft: -10,
    },
    chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
    chipsRow: { gap: spacing.sm, paddingRight: spacing.lg },
    rowBetween: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      gap: spacing.md,
    },
    fareRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
    secure: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6 },
    dims: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
    dim: { width: "47%", gap: 4 },
    docRow: {
      flexDirection: "row",
      alignItems: "center",
      gap: spacing.sm,
      minHeight: touchTargetMin,
    },
    tapMin: {
      minHeight: touchTargetMin,
      minWidth: touchTargetMin,
      alignItems: "center",
      justifyContent: "center",
    },
    doneWrap: { alignItems: "center", gap: spacing.md, paddingTop: spacing.xl },
    doneIcon: {
      width: 88,
      height: 88,
      borderRadius: 44,
      alignItems: "center",
      justifyContent: "center",
    },
    keyboardBar: {
      alignItems: "flex-end",
      backgroundColor: c.white,
      borderTopWidth: StyleSheet.hairlineWidth,
      borderTopColor: c.border,
      paddingHorizontal: spacing.md,
    },
    input: {
      minHeight: touchTargetMin + 4,
      borderWidth: 1,
      borderColor: c.border,
      borderRadius: radius.lg,
      paddingHorizontal: spacing.md,
      backgroundColor: c.grayBg,
      color: c.primary,
      fontSize: 16,
    },
  });
