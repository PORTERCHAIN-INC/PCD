/** Proof captured at a delivery stop, held in memory until Complete. */
export type PodDraft = {
  photoUrl: string | null;
  signature: string;
  /** Printed name of whoever signed (required with a signature, ≥2 characters). */
  signerName: string;
  otp: string;
  /** Receiver ID check (pharmacy / merchant id_required). The type only — never the ID number. */
  idType: string;
  idNameMatches: boolean;
};

export const emptyPodDraft = (): PodDraft => ({
  photoUrl: null,
  signature: "",
  signerName: "",
  otp: "",
  idType: "",
  idNameMatches: false,
});
