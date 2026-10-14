/** Spoken stop readout (expo-speech uses the phone's own TTS: free, offline). */
import { isPickup, KIND_LABEL, type DispatchStop } from "../dispatchRoute";

export function stopReadout(stop: DispatchStop, etaMin: number | null): string {
  const parts = [`Next: ${KIND_LABEL[stop.kind]}.`, stop.address ? `${stop.address}.` : ""];
  if (etaMin != null) parts.push(`About ${Math.max(1, Math.round(etaMin))} minutes.`);
  if (stop.boxes)
    parts.push(
      `${stop.boxes} ${stop.boxes === 1 ? "box" : "boxes"}${isPickup(stop.kind) ? " to load" : ""}.`
    );
  if (stop.liftgate) parts.push("Liftgate needed.");
  return parts.filter(Boolean).join(" ");
}

export async function speak(text: string): Promise<void> {
  try {
    const Speech = await import("expo-speech");
    Speech.stop();
    Speech.speak(text, { rate: 1.0, pitch: 1.0 });
  } catch {
    /* no TTS */
  }
}

export async function stopSpeaking(): Promise<void> {
  try {
    (await import("expo-speech")).stop();
  } catch {
    /* no TTS */
  }
}
