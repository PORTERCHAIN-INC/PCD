"use client";

import { useEffect, useRef } from "react";
import type { EChartsOption } from "echarts";
import * as echarts from "echarts";

type Props = {
  option: EChartsOption;
  height?: number;
  className?: string;
};

/** ECharts canvas — imported only via next/dynamic from ReportChart. */
export default function ReportChartInner({ option, height = 280, className }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    chart.setOption(option, { notMerge: true });
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
    // Mount once — option updates handled below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: true });
  }, [option]);

  return <div ref={ref} className={className} style={{ height, width: "100%" }} />;
}
