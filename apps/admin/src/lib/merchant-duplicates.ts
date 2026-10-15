import { adminFetch } from "@/lib/api";

const B = "/v1/admin/merchant-duplicates";

export type DuplicateItem = {
  merchant_id: string;
  company_name: string;
  email: string | null;
  created_at: string | null;
  match_merchant_id: string;
  match_company_name: string;
  match_email: string | null;
  score: number;
  reasons: string[];
  source: string | null;
  preview: Record<string, number>;
};

export const merchantDuplicates = {
  list: (t: string) => adminFetch<{ items: DuplicateItem[] }>(B, t),
  keepSeparate: (t: string, id: string) =>
    adminFetch<unknown>(`${B}/${id}/keep-separate`, t, { method: "POST" }),
  merge: (t: string, source: string, target: string) =>
    adminFetch<{ merge_id: string; moved: Record<string, number> }>(`${B}/merge`, t, {
      method: "POST",
      body: JSON.stringify({ source_merchant_id: source, target_merchant_id: target }),
    }),
  undo: (t: string, mergeId: string) =>
    adminFetch<unknown>(`${B}/merges/${mergeId}/undo`, t, { method: "POST" }),
};
