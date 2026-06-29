"use client";

export default function PlatformDashboardIllustration() {
  return (
    <div className="relative w-full aspect-[4/3] rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-sm overflow-hidden shadow-2xl shadow-black/20">
      <div className="absolute inset-0 grid-pattern opacity-20" aria-hidden />
      <div className="p-5 sm:p-6 h-full flex flex-col">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-white/20" />
            <div className="w-2.5 h-2.5 rounded-full bg-white/20" />
            <div className="w-2.5 h-2.5 rounded-full bg-white/20" />
          </div>
          <span className="text-[10px] font-medium text-white/40 uppercase tracking-wider">
            Dispatch OS
          </span>
        </div>
        <div className="grid grid-cols-3 gap-3 mb-4">
          {[
            { label: "Active", value: "24" },
            { label: "On-time", value: "99%" },
            { label: "Routes", value: "18" },
          ].map((stat) => (
            <div
              key={stat.label}
              className="rounded-xl bg-white/[0.06] border border-white/[0.08] p-3"
            >
              <p className="text-lg font-semibold text-white">{stat.value}</p>
              <p className="text-[10px] text-white/45 mt-0.5">{stat.label}</p>
            </div>
          ))}
        </div>
        <div className="flex-1 rounded-xl bg-white/[0.04] border border-white/[0.08] p-4 relative overflow-hidden">
          <svg viewBox="0 0 400 160" className="w-full h-full" aria-hidden>
            <path
              d="M20 120 Q80 40 140 80 T260 60 T380 40"
              fill="none"
              stroke="#2563eb"
              strokeWidth="2"
              strokeDasharray="6 4"
              className="animate-[route-dash_2s_linear_infinite]"
            />
            {[
              [20, 120],
              [140, 80],
              [260, 60],
              [380, 40],
            ].map(([cx, cy], i) => (
              <g key={i}>
                <circle cx={cx} cy={cy} r="6" fill="#2563eb" opacity="0.3" />
                <circle cx={cx} cy={cy} r="3" fill="#60a5fa" />
              </g>
            ))}
          </svg>
          <div className="absolute bottom-3 left-3 right-3 flex gap-2">
            {["Stop 1", "Stop 2", "Stop 3"].map((stop, i) => (
              <div
                key={stop}
                className="flex-1 h-8 rounded-lg bg-white/[0.06] border border-white/[0.06] flex items-center px-2"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-secondary mr-2" />
                <span className="text-[9px] text-white/50 truncate">{stop}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
