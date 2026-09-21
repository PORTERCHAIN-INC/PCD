export type StopExceptionCode =
  | "customer_not_available"
  | "closed"
  | "no_access"
  | "weather_ice"
  | "refused"
  | "damaged_parcel"
  | "unsafe"
  | "unable_to_deliver";

export type StopExceptionDef = {
  id: StopExceptionCode;
  label: string;
  retryable: boolean;
  photoRequired: boolean;
};

export const STOP_EXCEPTION_TYPES: StopExceptionDef[] = [
  {
    id: "customer_not_available",
    label: "Not home / no answer",
    retryable: true,
    photoRequired: false,
  },
  { id: "closed", label: "Business closed", retryable: true, photoRequired: false },
  {
    id: "no_access",
    label: "No access (condo / dock / buzzer)",
    retryable: true,
    photoRequired: false,
  },
  { id: "weather_ice", label: "Weather / ice", retryable: true, photoRequired: false },
  { id: "refused", label: "Receiver refused", retryable: false, photoRequired: true },
  { id: "damaged_parcel", label: "Parcel damaged", retryable: false, photoRequired: true },
  { id: "unsafe", label: "Unsafe stop", retryable: false, photoRequired: true },
  { id: "unable_to_deliver", label: "Unable to deliver", retryable: false, photoRequired: false },
];

export function stopExceptionById(id: string): StopExceptionDef | undefined {
  return STOP_EXCEPTION_TYPES.find((item) => item.id === id);
}
