"use client";

import { use, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import SupportDetailView from "@/components/support/SupportDetailView";
import { supportApi } from "@/lib/support";

export default function SupportDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const qc = useQueryClient();
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");

  const {
    data: detail,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["support-ticket", id],
    enabled,
    refetchInterval: 15_000,
    queryFn: async () => supportApi.detail(await getApiToken(), id),
  });

  const invalidate = useCallback(async () => {
    await qc.invalidateQueries({ queryKey: ["support-ticket", id] });
    await qc.invalidateQueries({ queryKey: ["support-tickets"] });
    await qc.invalidateQueries({ queryKey: ["support-dashboard"] });
    await refetch();
  }, [qc, id, refetch]);

  return (
    <SupportDetailView
      detail={detail ?? null}
      loading={isLoading}
      onStatus={(status) => {
        void (async () => {
          const token = await getApiToken();
          await supportApi.updateStatus(token, id, status);
          await invalidate();
        })();
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
  );
}
