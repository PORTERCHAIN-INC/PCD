"use client";

import {
  ReportChart as SharedReportChart,
  type ReportChartProps,
} from "@porterchain/ui/report-chart";

export {
  lineChartOption,
  sparklineOption,
  donutChartOption,
  roseChartOption,
  horizontalBarOption,
  funnelChartOption,
  compactTrendOption,
} from "@/components/reports/reportChartOptions";

export default function ReportChart(props: ReportChartProps) {
  return <SharedReportChart height={320} {...props} />;
}
