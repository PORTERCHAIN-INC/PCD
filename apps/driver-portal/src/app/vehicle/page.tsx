"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function VehicleRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/profile#vehicle");
  }, [router]);
  return null;
}
