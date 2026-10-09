export type PodDraft = {
  photoUrl: string | null;
  signature: string;
  barcode: string;
  otp: string;
  /** Receiver ID check (pharmacy / merchant id_required). Never the ID number. */
  idType: string;
  idNameMatches: boolean;
};

export const emptyPodDraft = (): PodDraft => ({
  photoUrl: null,
  signature: "",
  barcode: "",
  otp: "",
  idType: "",
  idNameMatches: false,
});
