"use client";

import { useEffect } from "react";
import { useRouter } from "@/i18n/navigation";

/** Legacy path — unified login handles all user types. */
export default function CustomerSignInRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/login");
  }, [router]);

  return null;
}
