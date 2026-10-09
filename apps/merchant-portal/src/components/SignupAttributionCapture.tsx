"use client";

import { useEffect } from "react";
import { rememberSignupAttribution } from "@/lib/signupAttribution";

/** Captures website utm_* / pc_vid hand-off params once per session. Renders nothing. */
export default function SignupAttributionCapture() {
  useEffect(() => {
    rememberSignupAttribution();
  }, []);
  return null;
}
