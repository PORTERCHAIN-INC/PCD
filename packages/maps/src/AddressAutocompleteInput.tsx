"use client";

import { useEffect, useId, useRef, useState } from "react";
import { fetchGeoSuggestions, resolveGeoPlace, type GeoSuggestion } from "./maps-core";
import type { BookingAddress } from "./types";

interface AddressAutocompleteInputProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  onPlaceSelect: (address: BookingAddress) => void;
  placeholder?: string;
  /** @deprecated No key is needed; ignored. */
  apiKey?: string;
  /** API base for /v1/geo; defaults to NEXT_PUBLIC_PORTERCHAIN_API_URL. */
  apiBase?: string;
  className?: string;
  fallbackClassName?: string;
}

const listStyle: React.CSSProperties = {
  position: "absolute",
  zIndex: 50,
  left: 0,
  right: 0,
  top: "calc(100% + 4px)",
  margin: 0,
  padding: "4px 0",
  listStyle: "none",
  background: "#ffffff",
  border: "1px solid rgba(10,22,40,0.12)",
  borderRadius: 16,
  boxShadow: "0 12px 32px rgba(10,22,40,0.14)",
  maxHeight: 320,
  overflowY: "auto",
};

export default function AddressAutocompleteInput({
  id,
  value,
  onChange,
  onPlaceSelect,
  placeholder,
  apiBase,
  className = "booking-address-autocomplete",
  fallbackClassName = "booking-address-fallback",
}: AddressAutocompleteInputProps) {
  const listId = useId();
  const [items, setItems] = useState<GeoSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const typed = useRef(false);
  const selectRef = useRef(onPlaceSelect);
  useEffect(() => {
    selectRef.current = onPlaceSelect;
  });

  useEffect(() => {
    const q = value.trim();
    if (!typed.current || q.length < 4) {
      setItems([]);
      return;
    }
    const ctl = new AbortController();
    const t = window.setTimeout(() => {
      fetchGeoSuggestions(q, { apiBase, signal: ctl.signal })
        .then((r) => {
          setItems(r);
          setActive(-1);
          setOpen(r.length > 0);
        })
        .catch(() => undefined);
    }, 450);
    return () => {
      window.clearTimeout(t);
      ctl.abort();
    };
  }, [value, apiBase]);

  const choose = (s: GeoSuggestion) => {
    typed.current = false;
    setOpen(false);
    setItems([]);
    onChange(s.formatted);
    void resolveGeoPlace({ id: s.id }, { apiBase }).then((addr) => {
      if (addr) selectRef.current(addr);
    });
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open || items.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => (i + 1) % items.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (i <= 0 ? items.length - 1 : i - 1));
    } else if (e.key === "Enter" && active >= 0) {
      e.preventDefault();
      choose(items[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div className={className} style={{ position: "relative" }}>
      <input
        id={id}
        type="text"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls={listId}
        aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
        value={value}
        onChange={(e) => {
          typed.current = true;
          onChange(e.target.value);
        }}
        onKeyDown={onKeyDown}
        onFocus={() => items.length > 0 && setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
        placeholder={placeholder}
        className={fallbackClassName}
        autoComplete="off"
        spellCheck={false}
      />
      {open && items.length > 0 && (
        <ul id={listId} role="listbox" style={listStyle}>
          {items.map((s, i) => (
            <li
              key={s.id}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(s);
              }}
              onMouseEnter={() => setActive(i)}
              style={{
                padding: "10px 16px",
                cursor: "pointer",
                background: i === active ? "rgba(10,22,40,0.06)" : "transparent",
                color: "#0a1628",
                fontSize: 15,
                lineHeight: 1.3,
              }}
            >
              <span style={{ fontWeight: 600 }}>{s.main}</span>
              {s.secondary && (
                <span style={{ display: "block", fontSize: 13, color: "rgba(10,22,40,0.65)" }}>
                  {s.secondary}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
