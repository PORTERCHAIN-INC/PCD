"use client";

import { useEffect, useRef } from "react";
import type { EChartsOption } from "echarts";
import * as echarts from "echarts";

type Props = {
  option: EChartsOption;
  height?: number;
  className?: string;
};

export default function ReportChart({ option, height = 320, className }: Props) {
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

export function lineChartOption(
  labels: string[],
  series: Array<{ name: string; data: number[]; color?: string }>
): EChartsOption {
  return {
    color: ["#2563eb", "#0ea5e9", "#10b981"],
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
    grid: { left: 48, right: 16, top: 24, bottom: 48 },
    xAxis: { type: "category", data: labels, boundaryGap: false },
    yAxis: { type: "value" },
    series: series.map((s) => ({
      name: s.name,
      type: "line",
      smooth: true,
      data: s.data,
      areaStyle: { opacity: 0.08 },
    })),
  };
}

export function barChartOption(labels: string[], values: number[], title?: string): EChartsOption {
  return {
    color: ["#2563eb"],
    title: title ? { text: title, left: 0, textStyle: { fontSize: 13, fontWeight: 600 } } : undefined,
    tooltip: { trigger: "axis" },
    grid: { left: 48, right: 16, top: title ? 40 : 24, bottom: 32 },
    xAxis: { type: "category", data: labels, axisLabel: { rotate: labels.length > 6 ? 30 : 0 } },
    yAxis: { type: "value" },
    series: [{ type: "bar", data: values, barMaxWidth: 48, itemStyle: { borderRadius: [4, 4, 0, 0] } }],
  };
}

export function pieChartOption(labels: string[], values: number[], title?: string): EChartsOption {
  return {
    color: ["#2563eb", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"],
    title: title ? { text: title, left: 0, textStyle: { fontSize: 13, fontWeight: 600 } } : undefined,
    tooltip: { trigger: "item" },
    series: [
      {
        type: "pie",
        radius: ["42%", "68%"],
        data: labels.map((name, i) => ({ name, value: values[i] })),
        label: { formatter: "{b}: {d}%" },
      },
    ],
  };
}
