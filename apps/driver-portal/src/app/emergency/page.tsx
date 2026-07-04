"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Siren } from "lucide-react";
import DriverShell from "@/components/DriverShell";
import { driverApi, hasDriverSession } from "@/lib/api";

export default function EmergencyPage() {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [sent, setSent] = useState(false);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    hasDriverSession().then((ok) => {
      if (!ok) router.replace("/login");
      else setAuthed(true);
    });
  }, [router]);

  const trigger = async () => {
    setPending(true);
    try {
      if (!navigator.geolocation) {
        await driverApi.emergency();
      } else {
        await new Promise<void>((resolve) => {
          navigator.geolocation.getCurrentPosition(
            async (pos) => {
              await driverApi.emergency({
                lat: pos.coords.latitude,
                lng: pos.coords.longitude,
              });
              resolve();
            },
            async () => {
              await driverApi.emergency();
              resolve();
            },
            { timeout: 8000 }
          );
        });
      }
      setSent(true);
    } finally {
      setPending(false);
    }
  };

  if (!authed) return null;

  return (
    <DriverShell>
      <div className="mx-auto flex max-w-lg flex-col items-center gap-6 rounded-2xl border-2 border-red-200 bg-red-50 p-8">
        <Siren className="h-12 w-12 text-red-600" />
        <h1 className="text-2xl font-bold text-red-800">Emergency SOS</h1>
        <p className="text-center text-red-700">
          Sends an immediate critical alert to Porterchain operations with your GPS location when
          available.
        </p>
        {sent ? (
          <p className="rounded-xl bg-white px-6 py-4 text-center text-sm font-semibold text-red-900">
            Alert sent. Operations has been notified. Stay safe.
          </p>
        ) : (
          <button
            type="button"
            onClick={trigger}
            disabled={pending}
            className="rounded-full bg-red-600 px-12 py-6 text-lg font-bold text-white shadow-lg disabled:opacity-50"
          >
            {pending ? "Sending…" : "SOS BUTTON"}
          </button>
        )}
        <button
          type="button"
          onClick={() => router.push("/support")}
          className="text-sm text-red-800 underline"
        >
          Back to Support
        </button>
      </div>
    </DriverShell>
  );
}
