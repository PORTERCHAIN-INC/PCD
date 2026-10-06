"use client";

import dynamic from "next/dynamic";
import type { EChartsOption } from "echarts";

export {
  lineChartOption,
  barChartOption,
  pieChartOption,
  sparklineOption,
  gaugeChartOption,
  donutChartOption,
  roseChartOption,
  radialBarOption,
  horizontalBarOption,
  funnelChartOption,
  compactTrendOption,
} from "@/components/reports/reportChartOptions";

const ReportChartInner = dynamic(() => import("@/components/reports/ReportChartInner"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full animate-pulse rounded-xl bg-primary/5 motion-reduce:animate-none" />
  ),
});

type Props = {
  option: EChartsOption;
  height?: number;
  className?: string;
  /** Hide the default “Loading chart…” min-height (use for sparklines). */
  compact?: boolean;
};

/** Lazy echarts shell — keeps dashboard first paint free of the chart bundle. */
export default function ReportChart({ option, height = 320, className, compact }: Props) {
  return (
    <div
      className={className}
      style={{ height, width: "100%", minHeight: compact ? height : undefined }}
    >
      <ReportChartInner option={option} height={height} className="h-full w-full" />
    </div>
  );
}
