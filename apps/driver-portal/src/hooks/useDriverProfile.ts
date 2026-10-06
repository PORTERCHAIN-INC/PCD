"use client";

import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { driverApi } from "@/lib/api";

export function useDriverProfile() {
  const qc = useQueryClient();
  const [uploading, setUploading] = useState<string | null>(null);
  const [verifyingIdentity, setVerifyingIdentity] = useState(false);
  const [startingBackground, setStartingBackground] = useState(false);
  const [submittingAbstract, setSubmittingAbstract] = useState(false);
  const profileQuery = useQuery({
    queryKey: ["driver-profile"],
    queryFn: async () => {
      const [snap, identity, background, abstract] = await Promise.all([
        driverApi.profile(),
        driverApi.identityVerificationStatus().catch(() => ({ enabled: false })),
        driverApi.backgroundCheckStatus().catch(() => ({ enabled: false })),
        driverApi.abstractStatus().catch(() => ({ enabled: false })),
      ]);
      return {
        data: snap,
        features: {
          identity: Boolean(identity.enabled),
          background: Boolean(background.enabled),
          abstract: Boolean(abstract.enabled),
        },
      };
    },
  });
  const data = profileQuery.data?.data ?? null;
  const features = profileQuery.data?.features ?? {
    identity: false,
    background: false,
    abstract: false,
  };
  const error =
    profileQuery.error instanceof Error
      ? profileQuery.error.message
      : profileQuery.error
        ? "profile_refresh_failed"
        : "";
  const loading = profileQuery.isLoading && !data;
  const refreshing = profileQuery.isFetching && Boolean(data);
  const refresh = useCallback(async () => {
    await qc.invalidateQueries({ queryKey: ["driver-profile"] });
  }, [qc]);

  const uploadDocument = useCallback(
    async (
      docType: string,
      fileUrl: string,
      metadata?: {
        expires_at?: string;
        policy_number?: string;
        provider?: string;
        plate_number?: string;
      }
    ) => {
      setUploading(docType);
      try {
        await driverApi.uploadDocument(docType, fileUrl, metadata);
        await refresh();
      } finally {
        setUploading(null);
      }
    },
    [refresh]
  );

  const uploadVehiclePhoto = useCallback(
    async (fileUrl: string, label?: string) => {
      setUploading("vehicle_photo");
      try {
        await driverApi.uploadVehiclePhoto(fileUrl, label ? { label } : undefined);
        await refresh();
      } finally {
        setUploading(null);
      }
    },
    [refresh]
  );

  const startIdentityVerification = useCallback(async () => {
    setVerifyingIdentity(true);
    try {
      const session = await driverApi.startIdentityVerification();
      if (session.mock) {
        await driverApi.mockCompleteIdentityVerification({
          session_id: session.session_id,
          verified: true,
        });
        await refresh();
        return { mock: true as const };
      }
      if (session.url) {
        window.location.assign(session.url);
        return { mock: false as const, redirected: true as const };
      }
      throw new Error("identity_session_missing_url");
    } finally {
      setVerifyingIdentity(false);
    }
  }, [refresh]);

  const startBackgroundCheck = useCallback(async () => {
    setStartingBackground(true);
    try {
      const started = await driverApi.startBackgroundCheck();
      if (started.already_cleared) {
        await refresh();
        return { already_cleared: true as const };
      }
      if (started.mock) {
        await driverApi.mockCompleteBackgroundCheck({
          invitation_id: started.invitation_id,
          result: "cleared",
        });
        await refresh();
        return { mock: true as const };
      }
      if (started.invitation_url) {
        window.open(started.invitation_url, "_blank", "noopener,noreferrer");
        await refresh();
        return { mock: false as const, opened: true as const };
      }
      throw new Error("background_invitation_missing_url");
    } finally {
      setStartingBackground(false);
    }
  }, [refresh]);

  const submitAbstract = useCallback(
    async (body: {
      file_url: string;
      license_class: string;
      demerit_points: number;
      has_active_suspension: boolean;
      expires_at?: string;
    }) => {
      setSubmittingAbstract(true);
      try {
        const result = await driverApi.submitAbstract(body);
        await refresh();
        return result;
      } finally {
        setSubmittingAbstract(false);
      }
    },
    [refresh]
  );

  return {
    data,
    error,
    loading,
    refreshing,
    uploading,
    verifyingIdentity,
    startingBackground,
    submittingAbstract,
    features,
    refresh,
    uploadDocument,
    uploadVehiclePhoto,
    startIdentityVerification,
    startBackgroundCheck,
    submitAbstract,
  };
}
