"use client";

import { useEffect } from "react";
import { onCLS, onINP, onLCP } from "web-vitals";
import { reportWebVitalMetric } from "@/lib/seo/web-vitals-report";

/** Lightweight CWV 2.0 RUM — INP focus for matrix + /business perf budgets. */
export default function WebVitalsReporter() {
  useEffect(() => {
    onINP(reportWebVitalMetric);
    onLCP(reportWebVitalMetric);
    onCLS(reportWebVitalMetric);
  }, []);

  return null;
}
