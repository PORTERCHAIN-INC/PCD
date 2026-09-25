"use client";

import dynamic from "next/dynamic";
import type { EChartsOption } from "echarts";

export {
  lineChartOption,
  barChartOption,
  pieChartOption,
} from "@/components/reports/reportChartOptions";

const ReportChartInner = dynamic(() => import("@/components/reports/ReportChartInner"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[200px] w-full items-center justify-center text-sm text-muted">
      Loading chart…
    </div>
  ),
});

type Props = {
  option: EChartsOption;
  height?: number;
  className?: string;
};

/** Lazy echarts shell — keeps dashboard first paint free of the chart bundle. */
export default function ReportChart(props: Props) {
  return <ReportChartInner {...props} />;
}
