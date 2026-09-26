"use client";

import dynamic from "next/dynamic";
import type { EChartsOption } from "echarts";

export {
  areaTrendOption,
  barChartOption,
  sparklineOption,
  donutChartOption,
  roseChartOption,
  funnelChartOption,
  compactTrendOption,
} from "@/components/charts/reportChartOptions";

const ReportChartInner = dynamic(() => import("@/components/charts/ReportChartInner"), {
  ssr: false,
  loading: () => null,
});

type Props = {
  option: EChartsOption;
  height?: number;
  className?: string;
  compact?: boolean;
};

/** Lazy echarts shell — keeps dashboard first paint free of the chart bundle. */
export default function ReportChart({ option, height = 280, className, compact }: Props) {
  return (
    <div
      className={className}
      style={{ height, width: "100%", minHeight: compact ? height : undefined }}
    >
      <ReportChartInner option={option} height={height} className="h-full w-full" />
    </div>
  );
}
