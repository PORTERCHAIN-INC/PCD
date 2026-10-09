/**
 * Home hero visual — no photo. An abstract GTA network: a dot grid clipped to a lakeshore-like
 * outline, three routes converging on a hub, and a few nodes that pulse (motion-safe only).
 * Inline SVG, desktop only, decorative; it never competes for LCP (the H1 is the LCP).
 */
const COLS = 34;
const ROWS = 22;
const STEP = 24;

/** Deterministic "density" field: denser toward the downtown hub, cut off by the lake (south). */
function dots() {
  const out: Array<[number, number, number]> = [];
  const hub = { x: 15, y: 13 };
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      const lake = r > 14 + Math.round(3 * Math.sin(c / 4.5)) - (c > 20 ? (c - 20) / 3 : 0);
      if (lake) continue;
      const d = Math.hypot(c - hub.x, (r - hub.y) * 1.3);
      const o = Math.max(0.12, 0.85 - d / 22);
      if ((c * 7 + r * 13) % 5 === 0 && d > 9) continue;
      out.push([c * STEP + 12, r * STEP + 12, Math.round(o * 100) / 100]);
    }
  }
  return out;
}

const DOTS = dots();
const HUB = [15 * STEP + 12, 13 * STEP + 12] as const;
const ROUTES = [
  `M ${3 * STEP + 12} ${4 * STEP + 12} C ${8 * STEP} ${5 * STEP}, ${10 * STEP} ${12 * STEP}, ${HUB[0]} ${HUB[1]}`,
  `M ${30 * STEP + 12} ${3 * STEP + 12} C ${25 * STEP} ${6 * STEP}, ${20 * STEP} ${8 * STEP}, ${HUB[0]} ${HUB[1]}`,
  `M ${31 * STEP + 12} ${12 * STEP + 12} C ${26 * STEP} ${15 * STEP}, ${21 * STEP} ${14 * STEP}, ${HUB[0]} ${HUB[1]}`,
];
const PULSES = [
  [3 * STEP + 12, 4 * STEP + 12],
  [30 * STEP + 12, 3 * STEP + 12],
  [31 * STEP + 12, 12 * STEP + 12],
] as const;

export default function HomeHeroImage() {
  return (
    <svg
      viewBox={`0 0 ${COLS * STEP} ${ROWS * STEP}`}
      preserveAspectRatio="xMidYMid slice"
      className="absolute inset-0 h-full w-full"
      aria-hidden
      focusable="false"
    >
      <g fill="#93c5fd">
        {DOTS.map(([x, y, o]) => (
          <circle key={`${x}-${y}`} cx={x} cy={y} r={2} opacity={o} />
        ))}
      </g>
      <g fill="none" stroke="#60a5fa" strokeWidth={2} strokeLinecap="round" opacity={0.55}>
        {ROUTES.map((d) => (
          <path key={d} d={d} className="hero-route" pathLength={1} />
        ))}
      </g>
      {PULSES.map(([x, y], i) => (
        <g key={`${x}-${y}`}>
          <circle cx={x} cy={y} r={5} fill="#ffffff" />
          <circle
            cx={x}
            cy={y}
            r={5}
            fill="none"
            stroke="#93c5fd"
            strokeWidth={2}
            className="hero-pulse"
            style={{ animationDelay: `${i * 0.8}s` }}
          />
        </g>
      ))}
      <circle cx={HUB[0]} cy={HUB[1]} r={9} fill="#1f56d8" stroke="#ffffff" strokeWidth={3} />
    </svg>
  );
}
