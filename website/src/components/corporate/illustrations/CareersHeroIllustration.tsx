"use client";

export default function CareersHeroIllustration() {
  return (
    <div className="relative w-full aspect-[5/4] max-w-lg mx-auto lg:mx-0 lg:ml-auto">
      <div className="absolute inset-0 rounded-3xl bg-secondary/10 blur-3xl scale-90" aria-hidden />
      <div className="relative rounded-2xl border border-white/10 bg-white/[0.05] backdrop-blur-sm overflow-hidden shadow-2xl shadow-black/25">
        <div className="absolute inset-0 grid-pattern opacity-30" aria-hidden />
        <div className="p-6 sm:p-8">
          <div className="flex items-center justify-between mb-6">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-white/40">
              Team · Canada
            </span>
            <div className="flex gap-1.5">
              <div className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
              <span className="text-[10px] text-white/50">Growing</span>
            </div>
          </div>

          <svg viewBox="0 0 320 220" className="w-full" aria-hidden>
            <defs>
              <linearGradient id="career-line" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#2563eb" stopOpacity="0.2" />
                <stop offset="50%" stopColor="#2563eb" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#60a5fa" stopOpacity="0.4" />
              </linearGradient>
            </defs>
            {[
              [60, 50, 160, 90],
              [160, 90, 260, 55],
              [160, 90, 140, 160],
              [140, 160, 260, 175],
              [60, 50, 100, 140],
            ].map(([x1, y1, x2, y2], i) => (
              <line
                key={i}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="url(#career-line)"
                strokeWidth="1.5"
                strokeDasharray="4 3"
              />
            ))}
            {[
              { cx: 60, cy: 50, r: 22, label: "Ops" },
              { cx: 160, cy: 90, r: 28, label: "Eng" },
              { cx: 260, cy: 55, r: 20, label: "Sales" },
              { cx: 100, cy: 140, r: 18, label: "CS" },
              { cx: 140, cy: 160, r: 22, label: "Dispatch" },
              { cx: 260, cy: 175, r: 20, label: "Drivers" },
            ].map((node, i) => (
              <g key={i}>
                <circle cx={node.cx} cy={node.cy} r={node.r} fill="#2563eb" fillOpacity="0.15" />
                <circle
                  cx={node.cx}
                  cy={node.cy}
                  r={node.r - 6}
                  fill="#0a1628"
                  stroke="#2563eb"
                  strokeWidth="1.5"
                />
                <text
                  x={node.cx}
                  y={node.cy + 4}
                  textAnchor="middle"
                  fill="#ffffff"
                  fontSize="9"
                  fontWeight="600"
                  opacity="0.85"
                >
                  {node.label}
                </text>
              </g>
            ))}
          </svg>

          <div className="mt-5 grid grid-cols-3 gap-2">
            {[
              { label: "Teams", value: "7" },
              { label: "Cities", value: "3+" },
              { label: "Remote", value: "Yes" },
            ].map((stat) => (
              <div
                key={stat.label}
                className="rounded-xl bg-white/[0.06] border border-white/[0.08] px-3 py-2.5 text-center"
              >
                <p className="text-sm font-semibold text-white">{stat.value}</p>
                <p className="text-[9px] text-white/45 uppercase tracking-wider mt-0.5">
                  {stat.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
