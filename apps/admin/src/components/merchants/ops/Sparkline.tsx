/** Eight-week order sparkline. Pure SVG, no chart lib. */
export function Sparkline({
  values,
  width = 96,
  height = 28,
  label,
}: {
  values: number[];
  width?: number;
  height?: number;
  label?: string;
}) {
  const max = Math.max(1, ...values);
  const step = values.length > 1 ? width / (values.length - 1) : width;
  const pts = values.map(
    (v, i) => `${(i * step).toFixed(1)},${(height - 2 - (v / max) * (height - 4)).toFixed(1)}`
  );
  const last = values[values.length - 1] ?? 0;
  const first4 = values.slice(0, 4).reduce((a, b) => a + b, 0);
  const last4 = values.slice(-4).reduce((a, b) => a + b, 0);
  const down = first4 > 0 && last4 < first4 * 0.85;
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={label ?? `Orders per week: ${values.join(", ")}`}
      className="shrink-0 overflow-visible"
    >
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.75}
        strokeLinejoin="round"
        strokeLinecap="round"
        className={down ? "text-red-600" : "text-primary/60"}
      />
      {values.length > 0 && (
        <circle
          cx={(values.length - 1) * step}
          cy={height - 2 - (last / max) * (height - 4)}
          r={2.5}
          className={down ? "fill-red-600" : "fill-primary"}
        />
      )}
    </svg>
  );
}
