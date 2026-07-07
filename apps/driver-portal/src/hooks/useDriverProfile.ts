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
  const mounted = useRef(true);

  const refresh = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true);
    try {
      const snap = await driverApi.profile();
      if (mounted.current) {
        setData(snap);
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

  return {
    data,
    error,
    loading,
    refreshing,
    uploading,
    refresh: () => refresh(true),
    uploadDocument,
    uploadVehiclePhoto,
  };
}
