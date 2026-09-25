"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";
import { use } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { claimsApi } from "@/lib/claims";

const ClaimDetailView = dynamic(() => import("@/components/claims/ClaimDetailView"), {
  loading: () => <Spinner label="Loading…" />,
  ssr: false,
});

export default function ClaimDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const qc = useQueryClient();

  const {
    data: detail,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["claim", id],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => {
      const token = await getApiToken();
      return claimsApi.detail(token, id);
    },
  });

  async function action(fn: (token: string) => Promise<unknown>) {
    const token = await getApiToken();
    await fn(token);
    await qc.invalidateQueries({ queryKey: ["claim", id] });
    await qc.invalidateQueries({ queryKey: ["claims"] });
    await qc.invalidateQueries({ queryKey: ["claims-dashboard"] });
    void refetch();
  }

  return (
    <ClaimDetailView
      detail={detail ?? null}
      loading={isLoading}
      onStatus={(status) => void action((t) => claimsApi.updateStatus(t, id, status))}
      onAutoAssign={() => void action((t) => claimsApi.autoAssign(t, id))}
      onAddNote={(body) => void action((t) => claimsApi.addNote(t, id, body))}
      onAddEvidence={(name, type) =>
        void action((t) => claimsApi.addEvidence(t, id, { file_type: type, name }))
      }
      onSaveInvestigation={(data) => void action((t) => claimsApi.updateInvestigation(t, id, data))}
      onSaveCompensation={(approved) =>
        void action((t) => claimsApi.setCompensation(t, id, { approved_amount_cents: approved }))
      }
      onSaveInsurance={(provider) =>
        void action((t) => claimsApi.setInsurance(t, id, { provider }))
      }
    />
  );
}
