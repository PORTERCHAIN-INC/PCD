import type { EChartsOption } from "echarts";

export function lineChartOption(
  labels: string[],
  series: Array<{ name: string; data: number[]; color?: string }>,
  opts?: { markAnomalies?: boolean }
): EChartsOption {
  const markAnomalies = opts?.markAnomalies !== false;
  return {
    color: ["#2563eb", "#0ea5e9", "#10b981"],
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
    grid: { left: 48, right: 16, top: 24, bottom: 48 },
    xAxis: { type: "category", data: labels, boundaryGap: false },
    yAxis: { type: "value" },
    series: series.map((s, idx) => {
      const markPoint =
        markAnomalies && idx === 0 && s.data.length >= 3
          ? anomalyMarkPoints(s.data, labels)
          : undefined;
      return {
        name: s.name,
        type: "line" as const,
        smooth: true,
        data: s.data,
        areaStyle: { opacity: 0.08 },
        markPoint,
        markLine:
          markAnomalies && idx === 0 && s.data.length >= 2
            ? {
                silent: true,
                symbol: "none",
                lineStyle: { type: "dashed", color: "#94a3b8", width: 1 },
                data: [{ type: "average", name: "Avg" }],
              }
            : undefined,
      };
    }),
  };
}

/** Flag points >1.5σ above/below the series mean. */
function anomalyMarkPoints(data: number[], labels: string[]) {
  const mean = data.reduce((a, b) => a + b, 0) / data.length;
  const variance = data.reduce((a, b) => a + (b - mean) ** 2, 0) / data.length;
  const std = Math.sqrt(variance);
  if (std === 0) return undefined;
  const points = data
    .map((v, i) => ({ v, i, z: Math.abs(v - mean) / std }))
    .filter((p) => p.z >= 1.5)
    .slice(0, 4)
    .map((p) => ({
      name: labels[p.i] ?? String(p.i),
      coord: [p.i, p.v] as [number, number],
      value: p.v,
      itemStyle: { color: p.v >= mean ? "#10b981" : "#f59e0b" },
    }));
  if (!points.length) return undefined;
  return {
    symbol: "pin",
    symbolSize: 36,
    label: { fontSize: 10 },
    data: points,
  };
}

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

export function gaugeChartOption(
  value: number,
  opts?: { name?: string; max?: number; dangerBelow?: number }
): EChartsOption {
  const max = opts?.max ?? 100;
  const dangerBelow = opts?.dangerBelow ?? 70;
  const clamped = Math.max(0, Math.min(max, value));
  const color =
    clamped < dangerBelow ? "#f59e0b" : clamped < dangerBelow + 15 ? "#0ea5e9" : "#10b981";
  return {
    series: [
      {
        type: "gauge",
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max,
        progress: { show: true, width: 10, itemStyle: { color } },
        axisLine: { lineStyle: { width: 10, color: [[1, "#e2e8f0"]] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        anchor: { show: false },
        title: {
          show: Boolean(opts?.name),
          offsetCenter: [0, "68%"],
          fontSize: 11,
          color: "#64748b",
        },
        detail: {
          valueAnimation: true,
          formatter: "{value}%",
          fontSize: 18,
          fontWeight: 700,
          color: "#0f172a",
          offsetCenter: [0, "20%"],
        },
        data: [{ value: Math.round(clamped * 10) / 10, name: opts?.name ?? "" }],
      },
    ],
  };
}

export function barChartOption(labels: string[], values: number[], title?: string): EChartsOption {
  return {
    color: ["#2563eb"],
    title: title
      ? { text: title, left: 0, textStyle: { fontSize: 13, fontWeight: 600 } }
      : undefined,
    tooltip: { trigger: "axis" },
    grid: { left: 48, right: 16, top: title ? 40 : 24, bottom: 32 },
    xAxis: { type: "category", data: labels, axisLabel: { rotate: labels.length > 6 ? 30 : 0 } },
    yAxis: { type: "value" },
    series: [
      { type: "bar", data: values, barMaxWidth: 48, itemStyle: { borderRadius: [4, 4, 0, 0] } },
    ],
  };
}

export function pieChartOption(labels: string[], values: number[], title?: string): EChartsOption {
  return {
    color: ["#2563eb", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#64748b"],
    title: title
      ? { text: title, left: 0, textStyle: { fontSize: 13, fontWeight: 600 } }
      : undefined,
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

/** Hollow donut — good for order / CRM mix. */
export function donutChartOption(
  slices: Array<{ name: string; value: number }>,
  opts?: { title?: string; centerLabel?: string }
): EChartsOption {
  const data = slices.filter((s) => s.value > 0);
  const safe = data.length ? data : [{ name: "None", value: 1 }];
  return {
    color: ["#2563eb", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#64748b"],
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

/** Nightingale rose — capacity / funnel drama without a second chart kit. */
export function roseChartOption(
  slices: Array<{ name: string; value: number }>,
  title?: string
): EChartsOption {
  return {
    color: ["#2563eb", "#38bdf8", "#10b981", "#f59e0b", "#ef4444"],
    title: title
      ? { text: title, left: 0, textStyle: { fontSize: 12, fontWeight: 600, color: "#0a1628" } }
      : undefined,
    tooltip: { trigger: "item" },
    series: [
      {
        type: "pie",
        roseType: "radius",
        radius: ["18%", "70%"],
        center: ["50%", "55%"],
        itemStyle: { borderRadius: 5 },
        label: { fontSize: 11 },
        data: slices.filter((s) => s.value > 0),
      },
    ],
  };
}

/** Circular progress bars for ops pressure (legacy; prefer OpsPressureCard). */
export function radialBarOption(
  items: Array<{ name: string; value: number; max?: number }>
): EChartsOption {
  const max = Math.max(1, ...items.map((i) => i.max ?? Math.max(i.value, 1)));
  return {
    color: ["#2563eb", "#0ea5e9", "#f59e0b", "#ef4444"],
    tooltip: { trigger: "item" },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    polar: { radius: ["28%", "78%"] },
    angleAxis: { max, startAngle: 90, show: false },
    radiusAxis: {
      type: "category",
      data: items.map((i) => i.name),
      show: false,
    },
    series: [
      {
        type: "bar",
        coordinateSystem: "polar",
        data: items.map((i) => i.value),
        barWidth: 12,
        itemStyle: { borderRadius: 6 },
        label: {
          show: true,
          position: "middle",
          formatter: "{b}",
          fontSize: 10,
          color: "#0a1628",
        },
      },
    ],
  };
}

/** Horizontal bars — merchant / capacity leaderboards. */
export function horizontalBarOption(
  rows: Array<{ name: string; value: number }>,
  opts?: { valueLabel?: string; color?: string }
): EChartsOption {
  const asDollars = opts?.valueLabel === "cents";
  const data = (rows.length ? rows : [{ name: "—", value: 0 }]).map((r) => ({
    name: r.name,
    value: asDollars ? Math.round(r.value / 100) : r.value,
  }));
  return {
    color: [opts?.color ?? "#2563eb"],
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      valueFormatter: (v) => (asDollars ? `$${Number(v).toLocaleString("en-CA")}` : String(v)),
    },
    grid: { left: 8, right: 56, top: 8, bottom: 8, containLabel: true },
    xAxis: { type: "value", show: false },
    yAxis: {
      type: "category",
      data: data.map((r) => r.name).reverse(),
      axisLabel: { width: 88, overflow: "truncate", fontSize: 11, color: "#64748b" },
      axisTick: { show: false },
      axisLine: { show: false },
    },
    series: [
      {
        type: "bar",
        data: data.map((r) => r.value).reverse(),
        barMaxWidth: 18,
        itemStyle: { borderRadius: [0, 6, 6, 0] },
        label: {
          show: true,
          position: "right",
          fontSize: 11,
          color: "#0a1628",
          formatter: asDollars ? "${c}" : "{c}",
        },
      },
    ],
  };
}

/** Booking / pipeline funnel. */
export function funnelChartOption(
  stages: Array<{ name: string; value: number }>,
  opts?: { title?: string }
): EChartsOption {
  const data = stages.filter((s) => s.value >= 0);
  const safe = data.some((s) => s.value > 0) ? data : [{ name: "No data", value: 1 }];
  return {
    color: ["#2563eb", "#3b82f6", "#0ea5e9", "#38bdf8", "#94a3b8"],
    title: opts?.title
      ? {
          text: opts.title,
          left: 0,
          textStyle: { fontSize: 12, fontWeight: 600, color: "#0a1628" },
        }
      : undefined,
    tooltip: { trigger: "item", formatter: "{b}: {c}" },
    series: [
      {
        type: "funnel",
        left: "8%",
        width: "84%",
        top: opts?.title ? 36 : 12,
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

/** Compact dual-series area for the intelligence canvas. */
export function compactTrendOption(
  labels: string[],
  revenueDollars: number[],
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
        name: "Revenue",
        type: "line",
        smooth: true,
        showSymbol: false,
        areaStyle: { opacity: 0.12 },
        data: revenueDollars,
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
