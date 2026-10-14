/** Proof captured at a delivery stop, held in memory until Complete. */
export type PodDraft = {
  photoUrl: string | null;
  signature: string;
  otp: string;
  /** Receiver ID check (pharmacy / merchant id_required). The type only — never the ID number. */
  idType: string;
  idNameMatches: boolean;
};

export const emptyPodDraft = (): PodDraft => ({
  photoUrl: null,
  signature: "",
  otp: "",
  idType: "",
  idNameMatches: false,
});
