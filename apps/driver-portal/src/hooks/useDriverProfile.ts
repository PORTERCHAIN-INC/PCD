"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { driverApi } from "@/lib/api";
import type { DriverProfileSnapshot } from "@/lib/profile";

const POLL_MS = 30_000;

export function useDriverProfile() {
  const [data, setData] = useState<DriverProfileSnapshot | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [uploading, setUploading] = useState<string | null>(null);
  const [verifyingIdentity, setVerifyingIdentity] = useState(false);
  const [startingBackground, setStartingBackground] = useState(false);
  const [submittingAbstract, setSubmittingAbstract] = useState(false);
  const [features, setFeatures] = useState({
    identity: false,
    background: false,
    abstract: false,
  });
  const mounted = useRef(true);

  const refresh = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true);
    try {
      const [snap, identity, background, abstract] = await Promise.all([
        driverApi.profile(),
        driverApi.identityVerificationStatus().catch(() => ({ enabled: false })),
        driverApi.backgroundCheckStatus().catch(() => ({ enabled: false })),
        driverApi.abstractStatus().catch(() => ({ enabled: false })),
      ]);
      if (mounted.current) {
        setData(snap);
        setFeatures({
          identity: Boolean(identity.enabled),
          background: Boolean(background.enabled),
          abstract: Boolean(abstract.enabled),
        });
        setError("");
      }
    } catch (e) {
      if (mounted.current) setError(e instanceof Error ? e.message : "profile_refresh_failed");
    } finally {
      if (mounted.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    refresh();
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") refresh(true);
    }, POLL_MS);
    return () => {
      mounted.current = false;
      window.clearInterval(interval);
    };
  }, [refresh]);

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
        await refresh(true);
      } finally {
        if (mounted.current) setUploading(null);
      }
    },
    [refresh]
  );

  const uploadVehiclePhoto = useCallback(
    async (fileUrl: string, label?: string) => {
      setUploading("vehicle_photo");
      try {
        await driverApi.uploadVehiclePhoto(fileUrl, label ? { label } : undefined);
        await refresh(true);
      } finally {
        if (mounted.current) setUploading(null);
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
        await refresh(true);
        return { mock: true as const };
      }
      if (session.url) {
        window.location.assign(session.url);
        return { mock: false as const, redirected: true as const };
      }
      throw new Error("identity_session_missing_url");
    } finally {
      if (mounted.current) setVerifyingIdentity(false);
    }
  }, [refresh]);

  const startBackgroundCheck = useCallback(async () => {
    setStartingBackground(true);
    try {
      const started = await driverApi.startBackgroundCheck();
      if (started.already_cleared) {
        await refresh(true);
        return { already_cleared: true as const };
      }
      if (started.mock) {
        await driverApi.mockCompleteBackgroundCheck({
          invitation_id: started.invitation_id,
          result: "cleared",
        });
        await refresh(true);
        return { mock: true as const };
      }
      if (started.invitation_url) {
        window.open(started.invitation_url, "_blank", "noopener,noreferrer");
        await refresh(true);
        return { mock: false as const, opened: true as const };
      }
      throw new Error("background_invitation_missing_url");
    } finally {
      if (mounted.current) setStartingBackground(false);
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
        await refresh(true);
        return result;
      } finally {
        if (mounted.current) setSubmittingAbstract(false);
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
    refresh: () => refresh(true),
    uploadDocument,
    uploadVehiclePhoto,
    startIdentityVerification,
    startBackgroundCheck,
    submitAbstract,
  };
}
