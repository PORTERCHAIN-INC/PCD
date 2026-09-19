/** Custom event to focus / open the on-site Logistics line chat. */

export const OPEN_LOGISTICS_CHAT_EVENT = "pc:open-logistics-chat";

export const LOGISTICS_CHAT_ANCHOR_ID = "logistics-line";

export function openLogisticsChat(opts?: { scroll?: boolean }) {
  if (typeof window === "undefined") return;
  if (opts?.scroll !== false) {
    const el = document.getElementById(LOGISTICS_CHAT_ANCHOR_ID);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  window.dispatchEvent(new CustomEvent(OPEN_LOGISTICS_CHAT_EVENT));
}
