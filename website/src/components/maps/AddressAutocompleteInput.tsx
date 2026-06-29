"use client";

import { useEffect, useRef } from "react";
import { useMapsLibrary } from "@vis.gl/react-google-maps";
import {
  applyBookingAutocompleteStyles,
  GTA_LOCATION_BIAS,
  isGoogleMapsConfigured,
  placeDetailsToBookingAddress,
  type BookingAddress,
} from "@/lib/maps";

interface AddressAutocompleteInputProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  onPlaceSelect: (address: BookingAddress) => void;
  placeholder?: string;
}

export default function AddressAutocompleteInput({
  id,
  value,
  onChange,
  onPlaceSelect,
  placeholder,
}: AddressAutocompleteInputProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const places = useMapsLibrary("places");
  const autocompleteRef = useRef<google.maps.places.PlaceAutocompleteElement | null>(null);
  const onPlaceSelectRef = useRef(onPlaceSelect);
  const onChangeRef = useRef(onChange);

  useEffect(() => {
    onPlaceSelectRef.current = onPlaceSelect;
    onChangeRef.current = onChange;
  });

  useEffect(() => {
    if (!isGoogleMapsConfigured() || !places || !containerRef.current) return;
    if (autocompleteRef.current) return;

    const placeAutocomplete = new places.PlaceAutocompleteElement({
      includedRegionCodes: ["ca"],
      locationBias: GTA_LOCATION_BIAS,
      placeholder: placeholder ?? "",
      requestedRegion: "CA",
      noInputIcon: true,
    });

    placeAutocomplete.id = id;
    placeAutocomplete.className = "booking-place-autocomplete";
    applyBookingAutocompleteStyles(placeAutocomplete);

    const handleInput = () => {
      onChangeRef.current(placeAutocomplete.value);
    };

    const handleSelect = (event: Event) => {
      const selectEvent = event as google.maps.places.PlacePredictionSelectEvent;
      void (async () => {
        const address = await placeDetailsToBookingAddress(selectEvent.placePrediction.toPlace());
        if (!address) return;
        onChangeRef.current(address.formatted);
        onPlaceSelectRef.current(address);
      })();
    };

    placeAutocomplete.addEventListener("input", handleInput);
    placeAutocomplete.addEventListener("gmp-select", handleSelect);

    containerRef.current.appendChild(placeAutocomplete);
    autocompleteRef.current = placeAutocomplete;

    return () => {
      placeAutocomplete.removeEventListener("input", handleInput);
      placeAutocomplete.removeEventListener("gmp-select", handleSelect);
      placeAutocomplete.remove();
      autocompleteRef.current = null;
    };
  }, [places, id, placeholder]);

  useEffect(() => {
    const el = autocompleteRef.current;
    if (!el || el.value === value) return;
    el.value = value;
  }, [value]);

  if (!isGoogleMapsConfigured()) {
    return (
      <input
        id={id}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="booking-address-fallback"
        autoComplete="off"
      />
    );
  }

  return <div ref={containerRef} className="booking-address-autocomplete" />;
}
