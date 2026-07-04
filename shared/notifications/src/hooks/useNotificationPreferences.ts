import { useCallback, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { NotificationCenterAdapter, NotificationPreference } from "../types";

export function useNotificationPreferences(adapter: NotificationCenterAdapter) {
  const queryClient = useQueryClient();
  const enabled = Boolean(adapter.getPreferences && adapter.updatePreference);

  const query = useQuery({
    queryKey: ["notifications", "preferences"],
    queryFn: () => adapter.getPreferences!(),
    enabled,
  });

  const [saving, setSaving] = useState<string | null>(null);

  const update = useCallback(
    async (pref: Partial<NotificationPreference> & { category: string }) => {
      if (!adapter.updatePreference) return;
      setSaving(pref.category);
      try {
        await adapter.updatePreference(pref);
        await queryClient.invalidateQueries({ queryKey: ["notifications", "preferences"] });
      } finally {
        setSaving(null);
      }
    },
    [adapter, queryClient]
  );

  return {
    preferences: query.data ?? [],
    isLoading: query.isLoading,
    isSaving: saving,
    update,
    enabled,
  };
}
