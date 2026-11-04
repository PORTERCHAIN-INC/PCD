import { test } from "node:test";
import assert from "node:assert/strict";
import {
  classifyIntent,
  contactPrompt,
  extractEmail,
  extractPhone,
  extractTrackingNumber,
  meetingTypeFrom,
  parseSlotChoice,
} from "./guide-rules";

test("classifies intents", () => {
  assert.equal(classifyIntent("Where is my parcel?"), "track");
  assert.equal(classifyIntent("Can we schedule a call"), "book");
  assert.equal(classifyIntent("How much for a pallet?"), "quote");
  assert.equal(classifyIntent("ops@acme.ca"), "contact");
  assert.equal(classifyIntent("Do you cover Ottawa?"), "question");
});

test("extracts contact details", () => {
  assert.equal(extractEmail("me: Ravi@Acme.CA thanks"), "ravi@acme.ca");
  assert.equal(extractPhone("call 416-555-0199"), "+14165550199");
  assert.equal(extractPhone("+1 (647) 555 0100"), "+16475550100");
  assert.equal(extractPhone("no number here"), undefined);
});

test("tracking, slots, meeting type, contact prompt", () => {
  assert.equal(extractTrackingNumber("track PC-ABC123 please"), "PC-ABC123");
  assert.equal(parseSlotChoice("2"), 1);
  assert.equal(parseSlotChoice("option 4"), 3);
  assert.equal(parseSlotChoice("tomorrow"), undefined);
  assert.equal(meetingTypeFrom("visit your office"), "meeting");
  assert.equal(meetingTypeFrom("phone call"), "call");
  assert.equal(contactPrompt({ stage: "capture", email: "a@b.co", phone: "+1" }), null);
  assert.match(contactPrompt({ stage: "capture", email: "a@b.co" }) ?? "", /mobile/);
});
