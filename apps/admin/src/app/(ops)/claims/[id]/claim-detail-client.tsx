"use client";

import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";
import { startTransition, useOptimistic, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { claimsApi, type ClaimDetail } from "@/lib/claims";

const ClaimDetailView = dynamic(() => import("@/components/claims/ClaimDetailView"), {
  loading: () => <PageSkeleton rows={4} />,
});

export default function ClaimDetailClient({ id }: { id: string }) {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const qc = useQueryClient();
  const [announce, setAnnounce] = useState<string | null>(null);

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

  const [optimisticDetail, setOptimisticStatus] = useOptimistic(
    detail ?? null,
    (current: ClaimDetail | null, status: string) =>
      current ? { ...current, status, display_status: status } : current
  );

  async function action(fn: (token: string) => Promise<unknown>) {
    const token = await getApiToken();
    await fn(token);
    await qc.invalidateQueries({ queryKey: ["claim", id] });
    await qc.invalidateQueries({ queryKey: ["claims"] });
    await qc.invalidateQueries({ queryKey: ["claims-dashboard"] });
    void refetch();
  }

  return (
    <>
      {announce ? (
        <p className="sr-only" role="status" aria-live="polite">
          {announce}
        </p>
      ) : null}
      <ClaimDetailView
        detail={optimisticDetail}
        loading={isLoading && !detail}
        onStatus={(status) => {
          startTransition(async () => {
            setOptimisticStatus(status);
            setAnnounce(`Status updated to ${status.replace(/_/g, " ")}`);
            try {
              await action((t) => claimsApi.updateStatus(t, id, status));
            } catch {
              setAnnounce("Could not update status");
              void refetch();
            }
          });
        }}
        onAutoAssign={() => void action((t) => claimsApi.autoAssign(t, id))}
        onAddNote={(body) => void action((t) => claimsApi.addNote(t, id, body))}
        onAddEvidence={(name, type) =>
          void action((t) => claimsApi.addEvidence(t, id, { file_type: type, name }))
        }
        onSaveInvestigation={(data) =>
          void action((t) => claimsApi.updateInvestigation(t, id, data))
        }
        onSaveCompensation={(approved) =>
          void action((t) => claimsApi.setCompensation(t, id, { approved_amount_cents: approved }))
        }
        onSaveInsurance={(provider) =>
          void action((t) => claimsApi.setInsurance(t, id, { provider }))
        }
      />
    </>
  );
}
