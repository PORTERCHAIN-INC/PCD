/**
 * Core Web Vitals RUM — reports INP, LCP, CLS to GA4 + internal analytics.
 */

import type { Metric } from "web-vitals";
import { track, ANALYTICS_EVENTS } from "./analytics";
import {
  classifyPageRoute,
  isOverPerfBudget,
  PERF_BUDGET_INP_GOOD_MS,
  PERF_BUDGET_INP_POOR_MS,
  type PageRouteClass,
} from "./perf-budget";

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

function metricValueForPayload(metric: Metric): number {
  if (metric.name === "CLS") return Math.round(metric.value * 1000);
  return Math.round(metric.value);
}

function sendToGtag(metric: Metric, routeClass: PageRouteClass): void {
  if (typeof window === "undefined" || !window.gtag) return;
  window.gtag("event", metric.name, {
    value: metricValueForPayload(metric),
    metric_id: metric.id,
    metric_value: metric.value,
    metric_delta: metric.delta,
    metric_rating: metric.rating,
    page_route_class: routeClass,
    non_interaction: true,
  });
}

export function reportWebVitalMetric(metric: Metric): void {
  if (typeof window === "undefined") return;

  const pathname = window.location.pathname;
  const routeClass = classifyPageRoute(pathname);
  const value = metric.name === "CLS" ? metric.value : metric.value;

  track(ANALYTICS_EVENTS.WEB_VITAL, {
    metric_name: metric.name,
    metric_value: metricValueForPayload(metric),
    metric_rating: metric.rating,
    page_route_class: routeClass,
    over_budget:
      metric.name === "INP" || metric.name === "LCP" || metric.name === "CLS"
        ? isOverPerfBudget(metric.name, value)
        : false,
  });

  sendToGtag(metric, routeClass);

  if (
    process.env.NODE_ENV === "development" &&
    metric.name === "INP" &&
    value > PERF_BUDGET_INP_GOOD_MS
  ) {
    console.warn(
      `[perf] INP ${Math.round(value)}ms exceeds budget ${PERF_BUDGET_INP_GOOD_MS}ms on ${routeClass}:`,
      pathname
    );
  }

  if (metric.name === "INP" && value > PERF_BUDGET_INP_POOR_MS && routeClass !== "other") {
    track(ANALYTICS_EVENTS.WEB_VITAL_BUDGET_EXCEEDED, {
      metric_name: "INP",
      metric_value: Math.round(value),
      page_route_class: routeClass,
      budget_ms: PERF_BUDGET_INP_GOOD_MS,
    });
  }
}
