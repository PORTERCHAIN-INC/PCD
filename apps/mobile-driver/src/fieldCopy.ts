/** Driver-facing copy — never show Expo / CoreLocation stacks on the van screen. */

export function humanFieldCopy(raw: string | null | undefined): string | null {
  const key = (raw || "").trim();
  if (!key) return null;
  if (
    /kCLErrorDomain|getCurrentPositionAsync|Cannot obtain current location|location services are enabled/i.test(
      key
    )
  ) {
    return "Can't read GPS yet. Enable Location for Porterchain Driver.";
  }
  if (/Expo Go yields APNs|native EAS build required/i.test(key)) {
    return "Job-ring alerts need a physical device. This simulator cannot register FCM.";
  }
  if (key.startsWith("driver_onboarding_blocked:")) {
    return "Finish onboarding before field jobs.";
  }
  if (key === "location_unavailable" || key === "location_ping_failed") {
    return "Can't read GPS yet. Enable Location for Porterchain Driver.";
  }
  if (key === "background_location_failed") {
    return "Background location is off — dispatch will only see you while the app is open.";
  }
  if (key === "not_at_stop") {
    return "GPS says you are not at this stop yet. Drive into the zone, then tap arrived.";
  }
  if (key === "pretrip_required") {
    return "Complete the 30-second vehicle check before starting shift.";
  }
  if (key === "shift_required") {
    return "Start shift (30-second vehicle check) before going online.";
  }
  return key;
}

export function fieldWarning(raw: string | null | undefined): string | null {
  const text = humanFieldCopy(raw);
  if (!text) return null;
  if (/^Location (idle|on|ping sent)|Background location active|FCM registered/i.test(text)) {
    return null;
  }
  if (/physical device|simulator cannot register FCM/i.test(text)) {
    return null;
  }
  return text;
}
