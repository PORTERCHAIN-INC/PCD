import { useQuery } from "@tanstack/react-query";
import { settingsApi, type UserDirectoryFilters, type UserDirectoryTab } from "@/lib/settings";
import { requireApiToken } from "./requireApiToken";

export function useUserDirectory(
  tab: UserDirectoryTab,
  filters: UserDirectoryFilters,
  enabled: boolean,
  getApiToken: () => Promise<string | null>
) {
  return useQuery({
    queryKey: ["settings-users", tab, filters],
    enabled,
    queryFn: async () => settingsApi.users(await requireApiToken(getApiToken), tab, filters),
  });
}

export function usersQueryKey(tab: UserDirectoryTab) {
  return ["settings-users", tab] as const;
}
