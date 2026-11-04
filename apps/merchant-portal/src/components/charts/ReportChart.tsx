"use client";

import {
  ReportChart as SharedReportChart,
  type ReportChartProps,
} from "@porterchain/ui/report-chart";

export {
  areaTrendOption,
  barChartOption,
  sparklineOption,
  donutChartOption,
  funnelChartOption,
} from "@/components/charts/reportChartOptions";

export default function ReportChart(props: ReportChartProps) {
  return <SharedReportChart height={280} {...props} />;
}
