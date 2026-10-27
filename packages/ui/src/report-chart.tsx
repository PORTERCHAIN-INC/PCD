"use client";

import dynamic from "next/dynamic";
import type { EChartsOption } from "echarts";

const ReportChartInner = dynamic(() => import("./report-chart-inner"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full animate-pulse rounded-xl bg-primary/5 motion-reduce:animate-none" />
  ),
});

export type ReportChartProps = {
  option: EChartsOption;
  height?: number;
  className?: string;
  /** Hide the loading min-height (use for sparklines). */
  compact?: boolean;
};

/** Lazy echarts shell — keeps dashboard first paint free of the chart bundle. */
export function ReportChart({ option, height = 280, className, compact }: ReportChartProps) {
  return (
    <div
      className={className}
      style={{ height, width: "100%", minHeight: compact ? height : undefined }}
    >
      <ReportChartInner option={option} height={height} className="h-full w-full" />
    </div>
  );
}
