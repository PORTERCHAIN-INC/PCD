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
import { colors, radius, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";
import { CAPACITY_CLASS_OPTIONS, vehicleLabel as capacityVehicleLabel } from "@porterchain/types";
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
import {
  addressReady,
  dayChoices,
  dayLabel,
  parseDeclaredCents,
  slotsFor,
  timeLabel,
} from "../ui/bookRules";
import { formatCanadianPhone } from "../ui/canadaPhone";
import { Motion } from "../ui/Motion";
import { PrimaryButton } from "../ui/PrimaryButton";
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
  const [extraStop, setExtraStop] = useState<Address>(emptyAddress());
  const [pickupManual, setPickupManual] = useState(false);
  const [dropoffManual, setDropoffManual] = useState(false);
  const [stopManual, setStopManual] = useState(false);
  const [declared, setDeclared] = useState("");
  const [instructions, setInstructions] = useState("");
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
  const [error, setError] = useState<string | null>(null);

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
        const extra = payload.additional_stops?.[0];
        if (extra?.formatted) setExtraStop(extra);
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
        const extra = resumed.additional_stops?.[0];
        if (extra?.formatted) setExtraStop(extra);
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
      dropoff,
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
      additional_stops: extraStop.formatted.trim() ? [extraStop] : undefined,
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
    extraStop,
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
    if (extraStop.formatted.trim() && !addressReady(extraStop)) {
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
      if (booking.mock_checkout) {
        setDone(await mockComplete(quote.quote_id));
        setStep("done");
        return;
      }
      if (!booking.checkout_url) throw new Error("checkout_unavailable");
      await WebBrowser.openBrowserAsync(booking.checkout_url);
      setDone(await pollCheckout(quote.quote_id));
      setStep("done");
    } catch (err) {
      const raw = err instanceof Error ? err.message : "request_failed";
      setError(humanCustomerError(raw));
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

  return (
    <Screen>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardDismissMode="interactive"
          keyboardShouldPersistTaps="handled"
        >
          <Text style={styles.title}>Book delivery</Text>
          {step === "done" && done ? (
            <>
              <Motion name="shipment" size={140} />
              <Text style={styles.price}>{done.tracking_number}</Text>
              <Text style={styles.lede}>
                {done.booking_mode === "vehicle"
                  ? "Whole vehicle"
                  : done.parcels
                      ?.map((item) => item.preset_label)
                      .filter(Boolean)
                      .join(", ") || `${done.parcels?.length || 0} parcels`}
                {done.vehicle_class ? ` · ${vehicleName(done.vehicle_class)}` : ""}
                {done.invoice_number ? ` · Invoice ${done.invoice_number}` : ""}
                {` · ${formatCad(done.amount_cents, done.currency)}`}
              </Text>
              <PrimaryButton
                label="Track shipment"
                onPress={() => onTracked(done.tracking_number)}
              />
            </>
          ) : (
            <>
              <View style={styles.chips}>
                {(["details", "quote", "pay"] as const).map((id) => {
                  const label = id === "details" ? "Details" : id === "quote" ? "Quote" : "Pay";
                  const open =
                    id === "details" ||
                    (id === "quote" && Boolean(quote)) ||
                    (id === "pay" && Boolean(quote));
                  return (
                    <Pressable
                      key={id}
                      disabled={!open}
                      onPress={() => {
                        if (id === "details") setQuote(null);
                        setStep(id);
                      }}
                      style={step === id ? styles.chipOn : styles.chip}
                    >
                      <Text style={step === id ? styles.chipOnText : styles.chipText}>{label}</Text>
                    </Pressable>
                  );
                })}
              </View>
              {step === "details" ? (
                <>
                  <Text style={styles.lede}>
                    Choose both addresses from Google. The quote uses those places.
                  </Text>
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
                    label="Dropoff"
                    value={dropoff}
                    onChange={(next) => {
                      setDropoff(next);
                      setQuote(null);
                    }}
                    accessoryId={KEYBOARD_BAR}
                    onManualOk={setDropoffManual}
                  />
                  <AddressField
                    label="Extra stop (optional)"
                    value={extraStop}
                    onChange={(next) => {
                      setExtraStop(next);
                      setQuote(null);
                    }}
                    accessoryId={KEYBOARD_BAR}
                    onManualOk={setStopManual}
                  />
                  <Text style={styles.label}>Vehicle</Text>
                  <View style={styles.chips}>
                    {vehicles.map((item) => (
                      <Pressable
                        key={item.id}
                        onPress={() => {
                          setVehicleClass(item.id);
                          setQuote(null);
                        }}
                        style={item.id === vehicleClass ? styles.chipOn : styles.chip}
                      >
                        <Text
                          style={item.id === vehicleClass ? styles.chipOnText : styles.chipText}
                        >
                          {item.label}
                          {includedKm ? ` · ${includedKm} km` : ""}
                        </Text>
                      </Pressable>
                    ))}
                  </View>
                  <Text style={styles.label}>Load</Text>
                  <View style={styles.chips}>
                    <Pressable
                      onPress={() => {
                        setBookingMode("parcels");
                        setQuote(null);
                      }}
                      style={bookingMode === "parcels" ? styles.chipOn : styles.chip}
                    >
                      <Text style={bookingMode === "parcels" ? styles.chipOnText : styles.chipText}>
                        Parcels
                      </Text>
                    </Pressable>
                    {wholeVehicleOk ? (
                      <Pressable
                        onPress={() => {
                          setBookingMode("vehicle");
                          setQuote(null);
                        }}
                        style={bookingMode === "vehicle" ? styles.chipOn : styles.chip}
                      >
                        <Text
                          style={bookingMode === "vehicle" ? styles.chipOnText : styles.chipText}
                        >
                          Whole vehicle
                        </Text>
                      </Pressable>
                    ) : null}
                  </View>
                  {nextVehicle ? (
                    <Pressable
                      onPress={() => {
                        setVehicleClass(nextVehicle.id);
                        setQuote(null);
                      }}
                      style={styles.chip}
                    >
                      <Text style={styles.chipText}>
                        This load needs {nextVehicle.label}. Switch vehicle.
                      </Text>
                    </Pressable>
                  ) : null}
                  {bookingMode === "parcels" ? (
                    <>
                      <Text style={styles.label}>Parcels</Text>
                      {rows.map((row, index) => (
                        <Pressable
                          key={`${row.preset_id}-${index}`}
                          onPress={() => setActiveParcel(index)}
                        >
                          <Text style={styles.lede}>
                            {index + 1}.{" "}
                            {presets.find((item) => item.id === row.preset_id)?.label ||
                              row.preset_id}
                            {row.instructions ? ` · ${row.instructions}` : ""}
                          </Text>
                        </Pressable>
                      ))}
                      <Text style={styles.label}>Size for parcel {activeParcel + 1}</Text>
                      <View style={styles.chips}>
                        {presets
                          .filter((item) => {
                            const vehicle = vehicles.find((row) => row.id === vehicleClass) as {
                              allowed_presets?: string[] | null;
                            };
                            const allowed = vehicle?.allowed_presets;
                            if (allowed?.length) return allowed.includes(item.id);
                            return (
                              vehicleClass !== "sedan_suv" ||
                              ["small", "medium", "large", "other"].includes(item.id)
                            );
                          })
                          .map((item) => (
                            <Pressable
                              key={item.id}
                              onPress={() =>
                                changeRows((current) =>
                                  current.map((row, index) =>
                                    index === activeParcel ? { ...row, preset_id: item.id } : row
                                  )
                                )
                              }
                              style={
                                rows[activeParcel]?.preset_id === item.id
                                  ? styles.chipOn
                                  : styles.chip
                              }
                            >
                              <Text
                                style={
                                  rows[activeParcel]?.preset_id === item.id
                                    ? styles.chipOnText
                                    : styles.chipText
                                }
                              >
                                {item.label}
                              </Text>
                            </Pressable>
                          ))}
                      </View>
                      <SuggestField
                        label="Note for this parcel"
                        value={rows[activeParcel]?.instructions ?? ""}
                        onChange={(value) =>
                          changeRows((current) =>
                            current.map((row, index) =>
                              index === activeParcel ? { ...row, instructions: value } : row
                            )
                          )
                        }
                        placeholder="Or type your own note"
                        suggestions={INSTRUCTIONS}
                        accessoryId={KEYBOARD_BAR}
                      />
                      {rows[activeParcel]?.preset_id === "other" ? (
                        <>
                          <SuggestField
                            label="Length (in)"
                            value={rows[activeParcel]?.length_in ?? ""}
                            onChange={(value) =>
                              changeRows((current) =>
                                current.map((row, index) =>
                                  index === activeParcel ? { ...row, length_in: value } : row
                                )
                              )
                            }
                            placeholder="Inches"
                            suggestions={[]}
                            keyboardType="decimal-pad"
                            accessoryId={KEYBOARD_BAR}
                          />
                          <SuggestField
                            label="Width (in)"
                            value={rows[activeParcel]?.width_in ?? ""}
                            onChange={(value) =>
                              changeRows((current) =>
                                current.map((row, index) =>
                                  index === activeParcel ? { ...row, width_in: value } : row
                                )
                              )
                            }
                            placeholder="Inches"
                            suggestions={[]}
                            keyboardType="decimal-pad"
                            accessoryId={KEYBOARD_BAR}
                          />
                          <SuggestField
                            label="Height (in)"
                            value={rows[activeParcel]?.height_in ?? ""}
                            onChange={(value) =>
                              changeRows((current) =>
                                current.map((row, index) =>
                                  index === activeParcel ? { ...row, height_in: value } : row
                                )
                              )
                            }
                            placeholder="Inches"
                            suggestions={[]}
                            keyboardType="decimal-pad"
                            accessoryId={KEYBOARD_BAR}
                          />
                          <SuggestField
                            label="Weight (lb)"
                            value={rows[activeParcel]?.weight_lb ?? ""}
                            onChange={(value) =>
                              changeRows((current) =>
                                current.map((row, index) =>
                                  index === activeParcel ? { ...row, weight_lb: value } : row
                                )
                              )
                            }
                            placeholder="Pounds"
                            suggestions={[]}
                            keyboardType="decimal-pad"
                            accessoryId={KEYBOARD_BAR}
                          />
                        </>
                      ) : null}
                      <Pressable
                        onPress={() => {
                          changeRows((current) => [...current, blankRow()]);
                          setActiveParcel(rows.length);
                          setQuote(null);
                        }}
                        style={styles.chip}
                      >
                        <Text style={styles.chipText}>Add parcel</Text>
                      </Pressable>
                      {rows.length > 1 ? (
                        <Pressable
                          onPress={() => {
                            changeRows((current) =>
                              current.filter((_, index) => index !== activeParcel)
                            );
                            setActiveParcel((current) => Math.max(0, current - 1));
                          }}
                          style={styles.chip}
                        >
                          <Text style={styles.chipText}>Remove parcel</Text>
                        </Pressable>
                      ) : null}
                    </>
                  ) : null}
                  {liveFare ? (
                    <Text style={styles.lede}>
                      Estimated fare {liveFare.amount}
                      {liveFare.km != null ? ` · ${liveFare.km} km` : ""}. Save the quote before
                      paying.
                    </Text>
                  ) : null}
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
                  <SuggestField
                    label="Instructions for the driver"
                    value={instructions}
                    onChange={setInstructions}
                    placeholder="Or type your own note"
                    suggestions={INSTRUCTIONS}
                    accessoryId={KEYBOARD_BAR}
                  />
                  <Text style={styles.label}>Phone</Text>
                  <TextInput
                    style={styles.input}
                    accessibilityLabel="Phone"
                    placeholder="+1 xxx-xxx-xxxx"
                    keyboardType="phone-pad"
                    textContentType="telephoneNumber"
                    value={phone}
                    onChangeText={(text) => setPhone(formatCanadianPhone(text))}
                    placeholderTextColor={colors.muted}
                    inputAccessoryViewID={KEYBOARD_BAR}
                  />
                  <TextInput
                    style={styles.input}
                    placeholder="Promo code"
                    autoCapitalize="characters"
                    value={promo}
                    onChangeText={(text) => {
                      setPromo(text);
                      setQuote(null);
                    }}
                    placeholderTextColor={colors.muted}
                    inputAccessoryViewID={KEYBOARD_BAR}
                  />
                  <View style={styles.chips}>
                    <Pressable
                      onPress={() => {
                        setLater(false);
                        setSlot(null);
                        setQuote(null);
                      }}
                      style={!later ? styles.chipOn : styles.chip}
                    >
                      <Text style={!later ? styles.chipOnText : styles.chipText}>
                        As soon as possible
                      </Text>
                    </Pressable>
                    <Pressable
                      onPress={() => {
                        setLater(true);
                        setQuote(null);
                      }}
                      style={later ? styles.chipOn : styles.chip}
                    >
                      <Text style={later ? styles.chipOnText : styles.chipText}>Schedule</Text>
                    </Pressable>
                  </View>
                  {later ? (
                    <>
                      <Text style={styles.label}>Pickup day</Text>
                      <View style={styles.chips}>
                        {days.map((day, index) => (
                          <Pressable
                            key={day.toISOString()}
                            onPress={() => {
                              setDayIndex(index);
                              setSlot(null);
                              setQuote(null);
                            }}
                            style={index === dayIndex ? styles.chipOn : styles.chip}
                          >
                            <Text style={index === dayIndex ? styles.chipOnText : styles.chipText}>
                              {dayLabel(day)}
                            </Text>
                          </Pressable>
                        ))}
                      </View>
                      <Text style={styles.label}>Pickup time</Text>
                      <View style={styles.chips}>
                        {slots.length ? (
                          slots.map((iso) => (
                            <Pressable
                              key={iso}
                              onPress={() => {
                                setSlot(iso);
                                setQuote(null);
                              }}
                              style={iso === slot ? styles.chipOn : styles.chip}
                            >
                              <Text style={iso === slot ? styles.chipOnText : styles.chipText}>
                                {timeLabel(iso)}
                              </Text>
                            </Pressable>
                          ))
                        ) : (
                          <Text style={styles.lede}>No times left today. Pick another day.</Text>
                        )}
                      </View>
                    </>
                  ) : null}
                  {error ? <Text style={styles.error}>{error}</Text> : null}
                  <PrimaryButton
                    label={busy ? "Working…" : "Get quote"}
                    disabled={busy}
                    onPress={() => void onQuote()}
                  />
                </>
              ) : null}
              {step === "quote" && quote ? (
                <>
                  <Text style={styles.lede}>{pickup.formatted}</Text>
                  <Text style={styles.lede}>{dropoff.formatted}</Text>
                  {later && slot ? (
                    <Text style={styles.lede}>
                      Pickup {dayLabel(new Date(slot))} · {timeLabel(slot)}
                    </Text>
                  ) : (
                    <Text style={styles.lede}>As soon as possible</Text>
                  )}
                  <Text style={styles.price}>
                    {quote.amount_display || formatCad(quote.amount_cents)}
                  </Text>
                  <Text style={styles.lede}>Expires {quote.expires_at}</Text>
                  {quote.pricing_breakdown.map((line) => (
                    <Text key={line.code} style={styles.lede}>
                      {line.label} · {formatCad(line.amount_cents)}
                    </Text>
                  ))}
                  {error ? <Text style={styles.error}>{error}</Text> : null}
                  <PrimaryButton label="Continue to pay" onPress={() => setStep("pay")} />
                  <Pressable
                    onPress={() => {
                      setQuote(null);
                      setStep("details");
                    }}
                  >
                    <Text style={styles.choice}>Edit details</Text>
                  </Pressable>
                </>
              ) : null}
              {step === "pay" && quote ? (
                <>
                  <Text style={styles.price}>
                    {quote.amount_display || formatCad(quote.amount_cents)}
                  </Text>
                  <Text style={styles.lede}>{phone || "No phone on this booking"}</Text>
                  <Check
                    label="I accept the terms"
                    checked={terms}
                    onPress={() => setTerms((v) => !v)}
                  />
                  <Check
                    label="I accept the privacy notice"
                    checked={privacy}
                    onPress={() => setPrivacy((v) => !v)}
                  />
                  <Check
                    label="No undeclared dangerous goods"
                    checked={dangerous}
                    onPress={() => setDangerous((v) => !v)}
                  />
                  {error ? <Text style={styles.error}>{error}</Text> : null}
                  <PrimaryButton
                    label={busy ? "Working…" : "Pay with Stripe"}
                    disabled={busy}
                    onPress={() => void onPay()}
                  />
                  <Pressable onPress={() => setStep("quote")}>
                    <Text style={styles.choice}>Back to quote</Text>
                  </Pressable>
                </>
              ) : null}
            </>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
      {Platform.OS === "ios" ? (
        <InputAccessoryView nativeID={KEYBOARD_BAR}>
          <View style={styles.keyboardBar}>
            <Pressable accessibilityRole="button" onPress={() => Keyboard.dismiss()} hitSlop={8}>
              <Text style={styles.keyboardHide}>Hide keyboard</Text>
            </Pressable>
          </View>
        </InputAccessoryView>
      ) : null}
    </Screen>
  );
}

function Check({
  label,
  checked,
  onPress,
}: {
  label: string;
  checked: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable accessibilityRole="checkbox" accessibilityState={{ checked }} onPress={onPress}>
      <Text style={styles.choice}>
        {checked ? "☑" : "☐"} {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  scroll: { gap: 10, paddingBottom: 32 },
  keyboardBar: {
    alignItems: "flex-end",
    backgroundColor: colors.grayBg,
    borderTopWidth: 1,
    borderTopColor: `${colors.primary}14`,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
  },
  keyboardHide: { ...typography.body, color: colors.secondary, fontWeight: "700" },
  title: { ...typography.title, fontSize: 30, color: colors.primary },
  lede: { ...typography.caption, color: colors.muted },
  label: { ...typography.caption, color: colors.muted },
  choice: { ...typography.body, color: colors.primary },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    backgroundColor: colors.white,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: `${colors.primary}18`,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  chipOn: {
    backgroundColor: colors.secondary,
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  chipText: { ...typography.caption, color: colors.primary, fontWeight: "600" },
  chipOnText: { ...typography.caption, color: colors.white, fontWeight: "700" },
  price: { ...typography.title, color: colors.primary },
  error: { ...typography.caption, color: colors.danger },
  input: {
    minHeight: touchTargetMin,
    borderWidth: 1,
    borderColor: `${colors.primary}26`,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.md,
    backgroundColor: colors.white,
    color: colors.primary,
  },
});
