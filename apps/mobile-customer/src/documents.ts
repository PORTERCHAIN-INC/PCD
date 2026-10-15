import * as WebBrowser from "expo-web-browser";
import { customerPortalUrl } from "./config";

/** Open the booking's documents in the customer portal (same sign-in), inside the app. */
export function openDocuments(trackingNumber: string) {
  return WebBrowser.openBrowserAsync(
    `${customerPortalUrl}/orders?docs=${encodeURIComponent(trackingNumber)}`,
    { presentationStyle: WebBrowser.WebBrowserPresentationStyle.PAGE_SHEET }
  );
}
