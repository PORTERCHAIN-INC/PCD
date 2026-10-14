/** Query hooks: cached, persisted, stale-while-revalidate. Mutations are optimistic. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchAppSettings,
  fetchDispatchRoute,
  fetchDocuments,
  fetchEarningsToday,
  fetchMonitoringPolicy,
  fetchSupportHub,
  fetchVehicle,
  saveAppSettings,
  uploadDocument,
  type DriverDocument,
} from "../api";
import { optimisticUpload } from "../docs";
import { mergeServer, toServer, type AppSettings } from "../settings";
import { toast } from "../ui/toast";
import { qk } from "./keys";
import { queryClient } from "./queryClient";

export const useDocuments = () =>
  useQuery({ queryKey: qk.documents, queryFn: fetchDocuments, staleTime: 5 * 60_000 });
export const useVehicle = () =>
  useQuery({ queryKey: qk.vehicle, queryFn: fetchVehicle, staleTime: 10 * 60_000 });
export const useSupportHub = () =>
  useQuery({ queryKey: qk.support, queryFn: fetchSupportHub, staleTime: 10 * 60_000 });
export const useEarnings = (enabled = true) =>
  useQuery({
    queryKey: qk.earnings,
    queryFn: fetchEarningsToday,
    enabled,
    refetchInterval: 5 * 60_000,
  });
export const usePolicy = () =>
  useQuery({ queryKey: qk.policy, queryFn: fetchMonitoringPolicy, staleTime: 60 * 60_000 });

let touchedLocally = false;
export const useServerSettings = () =>
  useQuery({
    queryKey: qk.settings,
    queryFn: async () => {
      const out = await fetchAppSettings();
      mergeServer(out.settings, touchedLocally);
      return out;
    },
    staleTime: 10 * 60_000,
  });

/** Save one setting: the phone changes instantly; the server copy follows (retried offline). */
export function useSaveSetting() {
  return useMutation({
    mutationFn: (patch: Partial<AppSettings>) => saveAppSettings(toServer(patch)),
    onMutate: () => {
      touchedLocally = true;
    },
    onSuccess: (out) => queryClient.setQueryData(qk.settings, out),
    retry: 3,
  });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { doc_type: string; file_url: string; expires_at: string | null }) =>
      uploadDocument({
        doc_type: v.doc_type,
        file_url: v.file_url,
        ...(v.expires_at ? { metadata: { expires_at: v.expires_at } } : {}),
      }),
    onMutate: async (v) => {
      await qc.cancelQueries({ queryKey: qk.documents });
      const prev = qc.getQueryData<{ documents: DriverDocument[] }>(qk.documents);
      if (prev)
        qc.setQueryData(qk.documents, {
          documents: optimisticUpload(prev.documents, v.doc_type, v.expires_at),
        });
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.documents, ctx.prev);
      toast.show("danger", "Upload failed", "Nothing changed. Try again with signal.");
    },
    onSuccess: () =>
      toast.show("success", "Sent for review", "Dispatch checks it within 1 business day."),
    onSettled: () => void qc.invalidateQueries({ queryKey: qk.documents }),
  });
}

/** Warm the cache right after sign-in and on every foreground. */
export function prefetchAll(): void {
  const q = queryClient;
  void q.prefetchQuery({ queryKey: qk.route, queryFn: fetchDispatchRoute });
  void q.prefetchQuery({ queryKey: qk.documents, queryFn: fetchDocuments, staleTime: 5 * 60_000 });
  void q.prefetchQuery({ queryKey: qk.vehicle, queryFn: fetchVehicle, staleTime: 10 * 60_000 });
  void q.prefetchQuery({ queryKey: qk.support, queryFn: fetchSupportHub, staleTime: 10 * 60_000 });
  void q.prefetchQuery({ queryKey: qk.earnings, queryFn: fetchEarningsToday });
}

/** Push / realtime: a route or job change invalidates exactly what it touches. */
export function invalidateFromPush(kind: string | undefined): void {
  const q = queryClient;
  if (!kind || /route|stop|job|order|dispatch/i.test(kind)) {
    void q.invalidateQueries({ queryKey: qk.route });
    void q.invalidateQueries({ queryKey: qk.handshake });
  }
  if (!kind || /doc|compliance|insurance|licen/i.test(kind))
    void q.invalidateQueries({ queryKey: qk.documents });
  if (!kind || /earn|payout|wallet/i.test(kind))
    void q.invalidateQueries({ queryKey: qk.earnings });
}

// ---------- Profile, pay, time, alerts, help (all cached + persisted; quiet refresh) ----------
import {
  createTicket,
  fetchEarnings,
  fetchInbox,
  fetchMyProfile,
  fetchSchedule,
  fetchStatements,
  fetchTickets,
  fetchTimesheets,
  markAllRead,
  patchMyProfile,
  saveSchedule,
  type InboxItem,
  type MeProfile,
  type ProfilePatch,
  type Schedule,
  type Ticket,
} from "../api";

export const useMyProfile = () =>
  useQuery({ queryKey: qk.profile, queryFn: fetchMyProfile, staleTime: 10 * 60_000 });
export const useEarningsFull = () =>
  useQuery({ queryKey: qk.earningsFull, queryFn: fetchEarnings, staleTime: 5 * 60_000 });
export const useStatements = () =>
  useQuery({ queryKey: qk.statements, queryFn: fetchStatements, staleTime: 60 * 60_000 });
export const useTimesheets = () =>
  useQuery({ queryKey: qk.timesheets, queryFn: () => fetchTimesheets(4), staleTime: 5 * 60_000 });
export const useSchedule = () =>
  useQuery({ queryKey: qk.schedule, queryFn: fetchSchedule, staleTime: 30 * 60_000 });
export const useInbox = () =>
  useQuery({ queryKey: qk.inbox, queryFn: fetchInbox, staleTime: 60_000 });
export const useTickets = () =>
  useQuery({ queryKey: qk.tickets, queryFn: fetchTickets, staleTime: 5 * 60_000 });

/** Profile save: the screen updates at once; rolled back with a toast if the server says no. */
export function useSaveProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: ProfilePatch) => patchMyProfile(patch),
    onMutate: async (patch) => {
      await qc.cancelQueries({ queryKey: qk.profile });
      const prev = qc.getQueryData<MeProfile>(qk.profile);
      if (prev) {
        const { photo, ...rest } = patch;
        qc.setQueryData(qk.profile, {
          ...prev,
          ...rest,
          ...(photo !== undefined ? { photo_url: photo } : {}),
        });
      }
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.profile, ctx.prev);
    },
    onSuccess: (out) => qc.setQueryData(qk.profile, out.profile),
  });
}

export function useSaveSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (s: Schedule) => saveSchedule(s),
    onMutate: (s) => {
      const prev = qc.getQueryData<{ schedule: Schedule; weekly_hours: number }>(qk.schedule);
      qc.setQueryData(qk.schedule, { schedule: s, weekly_hours: prev?.weekly_hours ?? 0 });
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.schedule, ctx.prev);
    },
    onSuccess: (out) => qc.setQueryData(qk.schedule, out),
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: markAllRead,
    onMutate: () => {
      const prev = qc.getQueryData<{ unread_count: number; items: InboxItem[] }>(qk.inbox);
      if (prev)
        qc.setQueryData(qk.inbox, {
          unread_count: 0,
          items: prev.items.map((i) => ({ ...i, is_read: true })),
        });
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.inbox, ctx.prev);
    },
  });
}

export function useCreateTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createTicket,
    onSuccess: (t) => {
      const prev = qc.getQueryData<{ tickets: Ticket[] }>(qk.tickets);
      qc.setQueryData(qk.tickets, { tickets: [t, ...(prev?.tickets ?? [])] });
    },
  });
}
