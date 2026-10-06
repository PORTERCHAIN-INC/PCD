"use client";

import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";
import { startTransition, useCallback, useOptimistic, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { supportApi, type TicketDetail } from "@/lib/support";

const SupportDetailView = dynamic(() => import("@/components/support/SupportDetailView"), {
  loading: () => <PageSkeleton rows={4} />,
});

export default function SupportDetailClient({ id }: { id: string }) {
  const qc = useQueryClient();
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  const [announce, setAnnounce] = useState<string | null>(null);

  const {
    data: detail,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["support-ticket", id],
    enabled,
    queryFn: async () => supportApi.detail(await getApiToken(), id),
  });

  const [optimisticDetail, setOptimisticStatus] = useOptimistic(
    detail ?? null,
    (current: TicketDetail | null, status: string) =>
      current ? { ...current, status, display_status: status } : current
  );

  const invalidate = useCallback(async () => {
    await qc.invalidateQueries({ queryKey: ["support-ticket", id] });
    await qc.invalidateQueries({ queryKey: ["support-tickets"] });
    await qc.invalidateQueries({ queryKey: ["support-dashboard"] });
    await refetch();
  }, [qc, id, refetch]);

  return (
    <>
      {announce ? (
        <p className="sr-only" role="status" aria-live="polite">
          {announce}
        </p>
      ) : null}
      <SupportDetailView
        detail={optimisticDetail}
        loading={isLoading && !detail}
        onStatus={(status) => {
          startTransition(async () => {
            setOptimisticStatus(status);
            setAnnounce(`Status updated to ${status.replace(/_/g, " ")}`);
            try {
              const token = await getApiToken();
              await supportApi.updateStatus(token, id, status);
              await invalidate();
            } catch {
              setAnnounce("Could not update status");
              await invalidate();
            }
          });
        }}
        onAssign={() => {
          void (async () => {
            const agentId = window.prompt("Agent user ID");
            if (!agentId) return;
            const token = await getApiToken();
            await supportApi.assign(token, id, agentId);
            await invalidate();
          })();
        }}
        onAutoAssign={() => {
          void (async () => {
            const token = await getApiToken();
            await supportApi.autoAssign(token, id);
            await invalidate();
          })();
        }}
        onAddNote={(body, internal) => {
          void (async () => {
            const token = await getApiToken();
            await supportApi.addNote(token, id, body, internal, internal ? "note" : "email");
            await invalidate();
          })();
        }}
        onPauseSla={() => {
          void (async () => {
            const token = await getApiToken();
            await supportApi.pauseSla(token, id);
            await invalidate();
          })();
        }}
        onResumeSla={() => {
          void (async () => {
            const token = await getApiToken();
            await supportApi.resumeSla(token, id);
            await invalidate();
          })();
        }}
      />
    </>
  );
}
