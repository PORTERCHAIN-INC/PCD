/** Tiny EN/FR string table (Settings → Language). Add keys as screens are translated. */
import { useSettings } from "./settings";

const STR = {
  settings: { en: "Settings", fr: "Paramètres" },
  documents: { en: "Documents", fr: "Documents" },
  driving: { en: "Driving", fr: "Conduite" },
  navApp: { en: "Navigation app", fr: "Application de navigation" },
  voice: { en: "Voice readout", fr: "Lecture vocale" },
  driveAuto: { en: "Drive mode starts by itself", fr: "Mode conduite automatique" },
  display: { en: "Display & feel", fr: "Affichage et retour" },
  textSize: { en: "Text size", fr: "Taille du texte" },
  haptics: { en: "Haptics", fr: "Vibrations" },
  batterySaver: { en: "Battery saver below", fr: "Économie de batterie sous" },
  notifications: { en: "Notifications", fr: "Notifications" },
  notifyJobs: { en: "New jobs", fr: "Nouvelles courses" },
  notifyMessages: { en: "Messages from dispatch", fr: "Messages de la répartition" },
  notifyRoute: { en: "Route changes", fr: "Changements d'itinéraire" },
  notifyDocs: { en: "Document expiry", fr: "Expiration des documents" },
  language: { en: "Language", fr: "Langue" },
  privacy: { en: "Location & privacy", fr: "Localisation et confidentialité" },
  app: { en: "App", fr: "Application" },
  signOut: { en: "Sign out", fr: "Se déconnecter" },
  clearCache: { en: "Clear cached data", fr: "Effacer les données en cache" },
  vehicle: { en: "Vehicle", fr: "Véhicule" },
  upload: { en: "Upload", fr: "Téléverser" },
  replace: { en: "Replace", fr: "Remplacer" },
  updated: { en: "Updated", fr: "Mis à jour" },
  today: { en: "Today", fr: "Aujourd'hui" },
  job: { en: "Job", fr: "Course" },
  me: { en: "Me", fr: "Moi" },
} as const;

export type StrKey = keyof typeof STR;
export type Lang = "en" | "fr";

export function tr(key: StrKey, lang: Lang): string {
  return STR[key][lang] ?? STR[key].en;
}

export function useT(): (key: StrKey) => string {
  const { language } = useSettings();
  return (key) => tr(key, language);
}
