"use client";

import { useRouter } from "next/navigation";
import { driverApi } from "@/lib/api";

export default function EmergencyPage() {
  const router = useRouter();

  const trigger = async () => {
    if (!navigator.geolocation) {
      await driverApi.emergency();
    } else {
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          await driverApi.emergency({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        },
        async () => {
          await driverApi.emergency();
        }
      );
    }
    alert("Emergency alert sent to operations.");
    router.push("/dashboard");
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-red-50 p-8">
      <h1 className="text-2xl font-bold text-red-800">Emergency</h1>
      <p className="text-center text-red-700">Press to alert Porterchain operations immediately.</p>
      <button
        type="button"
        onClick={trigger}
        className="rounded-full bg-red-600 px-12 py-6 text-lg font-bold text-white shadow-lg"
      >
        SEND ALERT
      </button>
      <button
        type="button"
        onClick={() => router.push("/dashboard")}
        className="text-sm text-red-800 underline"
      >
        Cancel
      </button>
    </div>
  );
}
