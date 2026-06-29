"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import type { BookingAddress } from "@/lib/maps";
import {
  BOOKING_TO_CATALOG,
  catalogIdToBookingKey,
  type BookingVehicleKey,
} from "@/lib/vehicle-keys";

interface BookingContextValue {
  selectedVehicle: BookingVehicleKey;
  catalogSelectedId: string | null;
  bookingHighlight: boolean;
  pickup: BookingAddress | null;
  dropoff: BookingAddress | null;
  setSelectedVehicle: (vehicle: BookingVehicleKey) => void;
  selectVehicleFromCatalog: (catalogId: string) => void;
  setPickup: (address: BookingAddress | null) => void;
  setDropoff: (address: BookingAddress | null) => void;
  swapAddresses: () => void;
}

const BookingContext = createContext<BookingContextValue | null>(null);

function scrollToBooking() {
  const el = document.getElementById("book");
  if (!el) return;
  const navOffset =
    parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--nav-height")) || 64;
  const top = el.getBoundingClientRect().top + window.scrollY - navOffset - 16;
  window.scrollTo({ top, behavior: "smooth" });
}

export function BookingProvider({ children }: { children: ReactNode }) {
  const [selectedVehicle, setSelectedVehicleState] = useState<BookingVehicleKey>("cargoVan");
  const [catalogSelectedId, setCatalogSelectedId] = useState<string | null>(null);
  const [bookingHighlight, setBookingHighlight] = useState(false);
  const [pickup, setPickup] = useState<BookingAddress | null>(null);
  const [dropoff, setDropoff] = useState<BookingAddress | null>(null);

  const swapAddresses = useCallback(() => {
    setPickup((prevPickup) => {
      setDropoff(prevPickup);
      return dropoff;
    });
  }, [dropoff]);

  const setSelectedVehicle = useCallback((vehicle: BookingVehicleKey) => {
    setSelectedVehicleState(vehicle);
    setCatalogSelectedId(BOOKING_TO_CATALOG[vehicle] ?? null);
  }, []);

  const selectVehicleFromCatalog = useCallback((catalogId: string) => {
    const bookingKey = catalogIdToBookingKey(catalogId);
    setSelectedVehicleState(bookingKey);
    setCatalogSelectedId(catalogId);
    setBookingHighlight(true);

    window.setTimeout(scrollToBooking, 350);
    window.setTimeout(() => setBookingHighlight(false), 2500);
  }, []);

  return (
    <BookingContext.Provider
      value={{
        selectedVehicle,
        catalogSelectedId,
        bookingHighlight,
        pickup,
        dropoff,
        setSelectedVehicle,
        selectVehicleFromCatalog,
        setPickup,
        setDropoff,
        swapAddresses,
      }}
    >
      {children}
    </BookingContext.Provider>
  );
}

export function useBooking() {
  const ctx = useContext(BookingContext);
  if (!ctx) {
    throw new Error("useBooking must be used within BookingProvider");
  }
  return ctx;
}
