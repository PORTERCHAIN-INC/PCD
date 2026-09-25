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
export default function ReportChartInner({ option, height = 320, className }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chart.setOption(option);
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.dispose();
    };
  }, [option]);

  return <div ref={ref} className={className} style={{ height, width: "100%" }} />;
}
