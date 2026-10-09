import { describe, expect, it } from "vitest";
import {
  centsToDollars,
  dollarsToCents,
  formatPriceVersion,
  getPath,
  isPlaceholder,
  PRICE_BOOK_PLACEHOLDERS,
  setPath,
  wholeNumber,
} from "./price-book";

describe("price-book helpers", () => {
  it("reads and writes nested paths without mutating", () => {
    const book = { minimum: { cents: 6000 }, parcel_tiers: [{ cents_per_parcel: 400 }] };
    const next = setPath(book, "parcel_tiers.0.cents_per_parcel", 450);
    expect(getPath(next, "parcel_tiers.0.cents_per_parcel")).toBe(450);
    expect(book.parcel_tiers[0]!.cents_per_parcel).toBe(400);
    expect(getPath(setPath(book, "minimum.cents", 7000), "minimum.cents")).toBe(7000);
  });

  it("flags EXAMPLE placeholders including children", () => {
    expect(isPlaceholder("stop_price_cents", PRICE_BOOK_PLACEHOLDERS)).toBe(true);
    expect(isPlaceholder("dedicated.vehicles.cargo_van.hour_cents", PRICE_BOOK_PLACEHOLDERS)).toBe(
      true
    );
    expect(isPlaceholder("handling.tiers", PRICE_BOOK_PLACEHOLDERS)).toBe(false);
  });

  it("converts dollars and cents safely", () => {
    expect(centsToDollars(2000)).toBe("20.00");
    expect(dollarsToCents("27")).toBe(2700);
    expect(dollarsToCents("-5")).toBe(0);
    expect(dollarsToCents("abc")).toBe(0);
    expect(wholeNumber("4.7")).toBe(4);
  });

  it("formats the price version", () => {
    expect(formatPriceVersion({ version: 3 })).toBe("pv-3");
    expect(formatPriceVersion(null)).toBeNull();
  });
});
