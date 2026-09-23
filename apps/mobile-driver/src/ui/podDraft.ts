export type PodDraft = {
  photoUrl: string | null;
  signature: string;
  barcode: string;
  otp: string;
};

export const emptyPodDraft = (): PodDraft => ({
  photoUrl: null,
  signature: "",
  barcode: "",
  otp: "",
});
