"use client";

export default function TorontoOfficeIllustration() {
  return (
    <div className="relative w-full max-w-md mx-auto lg:mx-0 lg:ml-auto">
      <div className="absolute -inset-4 rounded-3xl bg-secondary/15 blur-2xl" aria-hidden />
      <div className="relative rounded-2xl border border-white/10 bg-white/[0.05] backdrop-blur-sm overflow-hidden shadow-2xl shadow-black/20">
        <div className="absolute inset-0 grid-pattern opacity-25" aria-hidden />
        <svg viewBox="0 0 360 280" className="w-full" aria-hidden>
          <defs>
            <linearGradient id="tower-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2563eb" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#0a1628" stopOpacity="0.9" />
            </linearGradient>
            <linearGradient id="sky-glow" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#2563eb" stopOpacity="0.05" />
            </linearGradient>
          </defs>
          <rect width="360" height="280" fill="url(#sky-glow)" />
          <ellipse cx="180" cy="250" rx="140" ry="18" fill="#2563eb" fillOpacity="0.12" />

          {/* CN Tower silhouette hint */}
          <path
            d="M290 240 L298 80 L302 80 L310 240 Z"
            fill="#2563eb"
            fillOpacity="0.2"
            stroke="#60a5fa"
            strokeWidth="0.75"
            strokeOpacity="0.4"
          />
          <circle cx="300" cy="72" r="4" fill="#60a5fa" fillOpacity="0.6" />

          {/* Main office tower */}
          <rect x="95" y="60" width="120" height="180" rx="4" fill="url(#tower-fill)" stroke="#2563eb" strokeWidth="1.2" strokeOpacity="0.5" />
          {Array.from({ length: 12 }).map((_, row) =>
            Array.from({ length: 4 }).map((_, col) => (
              <rect
                key={`${row}-${col}`}
                x={108 + col * 26}
                y={78 + row * 13}
                width="16"
                height="8"
                rx="1"
                fill={row % 3 === col % 2 ? "#60a5fa" : "#2563eb"}
                fillOpacity={0.15 + (row % 4) * 0.08}
              />
            ))
          )}

          {/* King St label */}
          <rect x="40" y="228" width="280" height="28" rx="6" fill="#0a1628" fillOpacity="0.6" stroke="#2563eb" strokeWidth="0.75" strokeOpacity="0.3" />
          <text x="180" y="246" textAnchor="middle" fill="#ffffff" fontSize="9" fontWeight="600" opacity="0.75">
            100 King Street West · Toronto
          </text>

          {/* P marker */}
          <circle cx="155" cy="155" r="18" fill="#2563eb" fillOpacity="0.9" />
          <text x="155" y="160" textAnchor="middle" fill="white" fontSize="14" fontWeight="700">
            P
          </text>
        </svg>
        <div className="px-5 pb-5">
          <div className="flex items-center gap-2 rounded-xl bg-white/[0.06] border border-white/[0.08] px-3 py-2.5">
            <div className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
            <span className="text-[10px] font-medium text-white/55 uppercase tracking-wider">
              Toronto HQ · Financial District
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
