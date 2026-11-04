import type { Lang } from "./copy";

/** Server scan advice (batch_engine.planner.scan_advice) -> what the driver should do, EN/FR. */
export type ScanAdvice = {
  action:
    | "unknown_label"
    | "duplicate"
    | "already_delivered"
    | "return_to_depot"
    | "hand_to_driver"
    | "not_this_route"
    | "load"
    | "deliver";
  exception?: boolean;
  parcel_id?: string;
  barcode?: string;
  recipient?: string | null;
  stop_seq?: number | null;
  unit?: string | null;
  handling?: string[];
  load_position?: number | null;
  to_driver_id?: string | null;
  owner_driver_id?: string | null;
  carry_for_driver_id?: string | null;
  next?: string[];
  instructions?: { id: string; text: string; priority: string }[];
};

const HANDLING: Record<Lang, Record<string, string>> = {
  en: {
    fragile: "Fragile",
    upright: "Keep upright",
    cold: "Keep cold",
    pharmacy: "Pharmacy — ID check",
    id_check: "ID check",
    signature: "Signature",
    dolly: "Dolly",
    high_value: "High value",
    contract: "Contract",
  },
  fr: {
    fragile: "Fragile",
    upright: "Garder debout",
    cold: "Garder au froid",
    pharmacy: "Pharmacie — pièce d'identité",
    id_check: "Pièce d'identité",
    signature: "Signature",
    dolly: "Diable",
    high_value: "Haute valeur",
    contract: "Contrat",
  },
};

export function handlingLabels(h: string[] = [], lang: Lang = "en"): string[] {
  return h.map((x) => HANDLING[lang][x] ?? x);
}

export function adviceText(a: ScanAdvice, lang: Lang = "en"): string {
  const fr = lang === "fr";
  const stop = a.stop_seq != null ? (fr ? `arrêt ${a.stop_seq}` : `stop ${a.stop_seq}`) : "";
  const unit = a.unit ? (fr ? `, unité ${a.unit}` : `, unit ${a.unit}`) : "";
  switch (a.action) {
    case "unknown_label":
      return fr
        ? "Étiquette inconnue — cherchez par adresse ou destinataire, ou photo + signalement"
        : "Unknown label — look up by address or recipient, or photo + flag";
    case "duplicate":
      return fr ? "Déjà scanné — exception enregistrée" : "Already scanned — exception logged";
    case "already_delivered":
      return fr ? "Déjà livré — ne pas charger" : "Already delivered — don't load";
    case "return_to_depot":
      return fr ? "Retour au dépôt" : "Return to depot";
    case "hand_to_driver":
      return fr
        ? `Remettre au livreur ${a.to_driver_id ?? ""}`.trim()
        : `Hand to driver ${a.to_driver_id ?? ""}`.trim();
    case "not_this_route":
      return fr ? "Pas sur votre tournée — ne pas charger" : "Not on your route — don't load";
    case "load": {
      const pos =
        a.load_position != null
          ? fr
            ? `Charger en position ${a.load_position}`
            : `Load position ${a.load_position}`
          : fr
            ? "Charger"
            : "Load";
      const carry = a.carry_for_driver_id
        ? fr
          ? ` (pour ${a.carry_for_driver_id})`
          : ` (for ${a.carry_for_driver_id})`
        : "";
      return `${pos}${carry}${stop ? ` — ${stop}${unit}` : ""}`;
    }
    case "deliver":
      return fr ? `Livrer — ${stop}${unit}` : `Deliver — ${stop}${unit}`;
  }
  return a.action;
}

export const ADVICE_ACTIONS = [
  "unknown_label",
  "duplicate",
  "already_delivered",
  "return_to_depot",
  "hand_to_driver",
  "not_this_route",
  "load",
  "deliver",
] as const;
