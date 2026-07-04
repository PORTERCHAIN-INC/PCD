"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function InsuranceRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/profile#insurance");
  }, [router]);
  return null;
}
