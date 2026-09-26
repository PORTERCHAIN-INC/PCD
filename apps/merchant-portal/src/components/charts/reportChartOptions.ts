import type { EChartsOption } from "echarts";

const BRAND = ["#2563eb", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#64748b"];

export function sparklineOption(data: number[], color = "#2563eb"): EChartsOption {
  return {
    animation: false,
    grid: { left: 0, right: 0, top: 4, bottom: 0 },
    xAxis: { type: "category", show: false, data: data.map((_, i) => String(i)) },
    yAxis: { type: "value", show: false, min: "dataMin", max: "dataMax" },
    series: [
      {
        type: "line",
        data,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 1.5, color },
        areaStyle: { color, opacity: 0.12 },
      },
    ],
  };
}

export function areaTrendOption(
  labels: string[],
  values: number[],
  opts?: { name?: string; color?: string; dollars?: boolean }
): EChartsOption {
  const color = opts?.color ?? "#2563eb";
  const asDollars = opts?.dollars === true;
  return {
    color: [color],
    tooltip: {
      trigger: "axis",
      valueFormatter: (v) => (asDollars ? `$${Number(v).toLocaleString("en-CA")}` : String(v)),
    },
    grid: { left: 40, right: 12, top: 16, bottom: 28 },
    xAxis: {
      type: "category",
      data: labels,
      boundaryGap: false,
      axisLabel: { fontSize: 10, color: "#64748b" },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { type: "dashed", color: "#e2e8f0" } },
      axisLabel: {
        fontSize: 10,
        formatter: asDollars ? "${value}" : "{value}",
      },
    },
    series: [
      {
        name: opts?.name ?? "Value",
        type: "line",
        smooth: true,
        showSymbol: values.length <= 8,
        symbolSize: 6,
        areaStyle: { opacity: 0.14 },
        data: asDollars ? values.map((v) => Math.round(v / 100)) : values,
      },
    ],
  };
}

export function barChartOption(
  labels: string[],
  values: number[],
  opts?: { dollars?: boolean; color?: string }
): EChartsOption {
  const asDollars = opts?.dollars === true;
  const data = asDollars ? values.map((v) => Math.round(v / 100)) : values;
  return {
    color: [opts?.color ?? "#2563eb"],
    tooltip: {
      trigger: "axis",
      valueFormatter: (v) => (asDollars ? `$${Number(v).toLocaleString("en-CA")}` : String(v)),
    },
    grid: { left: 40, right: 12, top: 16, bottom: 32 },
    xAxis: {
      type: "category",
      data: labels,
      axisLabel: { fontSize: 10, color: "#64748b", rotate: labels.length > 7 ? 30 : 0 },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { type: "dashed", color: "#e2e8f0" } },
      axisLabel: { fontSize: 10 },
    },
    series: [
      {
        type: "bar",
        data,
        barMaxWidth: 36,
        itemStyle: { borderRadius: [6, 6, 0, 0] },
      },
    ],
  };
}

export function donutChartOption(
  slices: Array<{ name: string; value: number }>,
  opts?: { centerLabel?: string }
): EChartsOption {
  const data = slices.filter((s) => s.value > 0);
  const safe = data.length ? data : [{ name: "No orders", value: 1 }];
  return {
    color: BRAND,
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: { bottom: 0, type: "scroll", textStyle: { fontSize: 11 } },
    series: [
      {
        type: "pie",
        radius: ["52%", "74%"],
        center: ["50%", "44%"],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
        label: {
          show: Boolean(opts?.centerLabel),
          position: "center",
          formatter: opts?.centerLabel ?? "",
          fontSize: 13,
          fontWeight: 700,
          color: "#0a1628",
        },
        data: safe,
      },
    ],
  };
}

export function roseChartOption(slices: Array<{ name: string; value: number }>): EChartsOption {
  return {
    color: ["#2563eb", "#38bdf8", "#10b981", "#f59e0b", "#ef4444"],
    tooltip: { trigger: "item" },
    series: [
      {
        type: "pie",
        roseType: "radius",
        radius: ["16%", "68%"],
        center: ["50%", "52%"],
        itemStyle: { borderRadius: 5 },
        label: { fontSize: 11 },
        data: slices.filter((s) => s.value > 0),
      },
    ],
  };
}

export function funnelChartOption(stages: Array<{ name: string; value: number }>): EChartsOption {
  const data = stages.filter((s) => s.value >= 0);
  const safe = data.some((s) => s.value > 0) ? data : [{ name: "No volume", value: 1 }];
  return {
    color: ["#2563eb", "#3b82f6", "#0ea5e9", "#38bdf8", "#94a3b8"],
    tooltip: { trigger: "item", formatter: "{b}: {c}" },
    series: [
      {
        type: "funnel",
        left: "8%",
        width: "84%",
        top: 12,
        bottom: 12,
        minSize: "18%",
        maxSize: "100%",
        sort: "descending",
        gap: 4,
        label: { fontSize: 11, color: "#0a1628" },
        itemStyle: { borderColor: "#fff", borderWidth: 2 },
        data: safe,
      },
    ],
  };
}

/** Dual axis: spend ($) + orders for owner / accounting canvas. */
export function compactTrendOption(
  labels: string[],
  spendDollars: number[],
  orders: number[]
): EChartsOption {
  return {
    color: ["#2563eb", "#0ea5e9"],
    tooltip: { trigger: "axis" },
    legend: { top: 0, right: 0, textStyle: { fontSize: 11 } },
    grid: { left: 40, right: 36, top: 28, bottom: 28 },
    xAxis: {
      type: "category",
      data: labels,
      boundaryGap: false,
      axisLabel: { fontSize: 10, color: "#64748b" },
    },
    yAxis: [
      {
        type: "value",
        name: "$",
        nameTextStyle: { fontSize: 10 },
        splitLine: { lineStyle: { type: "dashed", color: "#e2e8f0" } },
        axisLabel: { fontSize: 10 },
      },
      {
        type: "value",
        name: "ord",
        nameTextStyle: { fontSize: 10 },
        splitLine: { show: false },
        axisLabel: { fontSize: 10 },
      },
    ],
    series: [
      {
        name: "Spend",
        type: "line",
        smooth: true,
        showSymbol: false,
        areaStyle: { opacity: 0.12 },
        data: spendDollars,
      },
      {
        name: "Orders",
        type: "line",
        smooth: true,
        showSymbol: false,
        yAxisIndex: 1,
        data: orders,
      },
    ],
  };
}
