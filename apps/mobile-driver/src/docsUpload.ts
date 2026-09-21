/** Shared document upload helper for Docs + Onboarding screens. */

import { uploadDocument, uploadVehiclePhoto } from "./api";
import { pickDocumentPhotoDataUrl } from "./pod";

export const FALLBACK_DOC_TYPES = [
  { type: "license", label: "Driver license" },
  { type: "insurance", label: "Insurance" },
  { type: "vehicle_registration", label: "Vehicle registration" },
] as const;

export function uploadTypeForOnboardingStep(stepId: string): string | null {
  if (stepId === "license_verified") return "license";
  if (stepId === "insurance_verified") return "insurance";
  if (stepId === "vehicle_verified") return "vehicle_registration";
  return null;
}

export async function captureAndUploadDocument(docType: string): Promise<void> {
  const fileUrl = await pickDocumentPhotoDataUrl();
  await uploadDocument(docType, fileUrl);
}

export async function captureAndUploadVehiclePhoto(label?: string): Promise<void> {
  const fileUrl = await pickDocumentPhotoDataUrl();
  await uploadVehiclePhoto(fileUrl, label ? { label } : undefined);
}
