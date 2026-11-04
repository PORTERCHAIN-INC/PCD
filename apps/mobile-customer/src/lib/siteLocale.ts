/** L37: open website pages in the phone's language (en or fr) instead of a hard-coded /en. */
export function siteLocale(): "en" | "fr" {
  try {
    const loc = Intl.DateTimeFormat().resolvedOptions().locale || "en";
    return loc.toLowerCase().startsWith("fr") ? "fr" : "en";
  } catch {
    return "en";
  }
}
