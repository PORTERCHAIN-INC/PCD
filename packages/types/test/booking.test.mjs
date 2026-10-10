import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_DROPS,
  bookingText,
  buildQuoteInput,
  canAddDrop,
  cleanDrops,
  formatPrice,
  payBlocker,
  postalOf,
} from "../src/booking.ts";

const A = "100 King St W, Toronto, ON M5V 2T6";
const B = "5 Bloor St E, Toronto, ON M4W 1A8";
const C = "1 Yonge St, Toronto, ON M5E 1E5";

test("postal codes are normalised", () => {
  assert.equal(postalOf("x m5v2t6"), "M5V 2T6");
  assert.equal(postalOf("no code"), undefined);
});

test("single drop builds pickup + dropoff only", () => {
  const q = buildQuoteInput({ pickup: A, drops: [B], vehicle: "sedan_suv" }, 0);
  assert.equal(q.dropoff.postal, "M4W 1A8");
  assert.equal(q.additional_stops, undefined);
});

test("multi drop: last is the drop-off, the rest are stops in order", () => {
  const q = buildQuoteInput({ pickup: A, drops: [C, B], vehicle: "cargo_van" }, 0);
  assert.equal(q.dropoff.formatted, B);
  assert.deepEqual(
    q.additional_stops.map((s) => s.formatted),
    [C]
  );
});

test("drops are capped at five and incomplete trips give no quote", () => {
  assert.equal(cleanDrops(Array(8).fill(B)).length, MAX_DROPS);
  assert.equal(canAddDrop(Array(5).fill(B)), false);
  assert.equal(buildQuoteInput({ pickup: A, drops: ["Bloor"], vehicle: "sedan_suv" }), null);
});

test("price and copy are localised", () => {
  assert.equal(formatPrice(7910), "$79.10");
  assert.equal(formatPrice(7910, "fr"), "79,10 $");
  assert.equal(bookingText("fr", "dropN", { n: 2 }), "Livraison 2");
});

test("pay blocker order: trip then contact", () => {
  const draft = { pickup: A, drops: [B], vehicle: "sedan_suv", name: "", email: "", phone: "" };
  assert.equal(payBlocker(draft, false), "needTrip");
  assert.equal(payBlocker(draft, true), "needContact");
  assert.equal(
    payBlocker({ ...draft, name: "Al", email: "a@b.ca", phone: "4165550199" }, true),
    null
  );
});
