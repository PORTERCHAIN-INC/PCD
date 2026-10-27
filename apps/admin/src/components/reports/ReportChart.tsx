"use client";

import {
  ReportChart as SharedReportChart,
  type ReportChartProps,
} from "@porterchain/ui/report-chart";

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

export default function ReportChart(props: ReportChartProps) {
  return <SharedReportChart height={320} {...props} />;
}
