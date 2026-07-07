interface GtaSkylineProps {
  className?: string;
}

export default function GtaSkyline({ className = "" }: GtaSkylineProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 1440 520"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      preserveAspectRatio="xMidYMax slice"
      aria-hidden
    >
      <defs>
        <linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0a1628" stopOpacity="0" />
          <stop offset="100%" stopColor="#0a1628" stopOpacity="0.6" />
        </linearGradient>
        <linearGradient id="lakeGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1e3a5f" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#0a1628" stopOpacity="0.8" />
        </linearGradient>
        <linearGradient id="towerGlow" x1="0" y1="1" x2="0" y2="0">
          <stop offset="0%" stopColor="#2563eb" stopOpacity="0.15" />
          <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.5" />
        </linearGradient>
        <linearGradient id="accentLine" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#2563eb" stopOpacity="0" />
          <stop offset="50%" stopColor="#38bdf8" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#2563eb" stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* Lake Ontario */}
      <rect x="0" y="480" width="1440" height="40" fill="url(#lakeGrad)" />
      <path
        d="M0 492 Q360 478 720 488 T1440 482 L1440 520 L0 520 Z"
        fill="#1e3a5f"
        opacity="0.25"
      />

      {/* Distant buildings left */}
      <rect x="0" y="340" width="55" height="180" fill="#152238" />
      <rect x="60" y="300" width="48" height="220" fill="#1a2d4a" />
      <rect x="115" y="330" width="40" height="190" fill="#152238" />
      <rect x="160" y="270" width="65" height="250" fill="#1e3354" />
      <rect x="235" y="310" width="50" height="210" fill="#152238" />
      <rect x="290" y="250" width="42" height="270" fill="#1a2d4a" />

      {/* Rogers Centre dome */}
      <ellipse cx="380" cy="400" rx="75" ry="35" fill="#1e3354" />
      <path
        d="M305 400 Q380 340 455 400"
        stroke="#2563eb"
        strokeWidth="1.5"
        fill="none"
        opacity="0.35"
      />

      {/* Office towers cluster */}
      <rect x="460" y="220" width="55" height="300" fill="#1a2d4a" />
      <rect x="470" y="240" width="8" height="12" fill="#38bdf8" opacity="0.3" />
      <rect x="485" y="260" width="8" height="12" fill="#38bdf8" opacity="0.25" />
      <rect x="470" y="290" width="8" height="12" fill="#38bdf8" opacity="0.3" />

      <rect x="525" y="180" width="48" height="340" fill="#1e3354" />
      <rect x="580" y="240" width="60" height="280" fill="#152238" />

      {/* CN Tower — iconic silhouette */}
      <g>
        <rect x="668" y="60" width="14" height="380" fill="url(#towerGlow)" />
        <rect x="664" y="55" width="22" height="8" rx="2" fill="#38bdf8" opacity="0.6" />
        {/* Observation pod */}
        <ellipse
          cx="675"
          cy="200"
          rx="28"
          ry="12"
          fill="#1e3354"
          stroke="#2563eb"
          strokeWidth="1"
          opacity="0.9"
        />
        <rect x="647" y="195" width="56" height="10" rx="3" fill="#2563eb" opacity="0.35" />
        {/* Main shaft */}
        <path d="M671 68 L679 68 L677 440 L673 440 Z" fill="#2a4068" />
        <line x1="675" y1="80" x2="675" y2="430" stroke="#38bdf8" strokeWidth="0.5" opacity="0.4" />
        {/* Antenna */}
        <line x1="675" y1="55" x2="675" y2="20" stroke="#60a5fa" strokeWidth="2" />
        <circle cx="675" cy="18" r="3" fill="#38bdf8" opacity="0.8" />
        {/* Base */}
        <path d="M655 440 L695 440 L690 460 L660 460 Z" fill="#1a2d4a" />
      </g>

      {/* First Canadian Place area */}
      <rect x="720" y="120" width="52" height="400" fill="#1e3354" />
      <rect x="730" y="140" width="6" height="10" fill="#38bdf8" opacity="0.35" />
      <rect x="745" y="160" width="6" height="10" fill="#38bdf8" opacity="0.3" />

      <rect x="785" y="200" width="45" height="320" fill="#152238" />
      <rect x="840" y="160" width="38" height="360" fill="#1a2d4a" />
      <rect x="888" y="190" width="55" height="330" fill="#1e3354" />

      {/* Accent lit towers */}
      <rect x="955" y="100" width="32" height="420" fill="#1a2d4a" />
      <rect x="962" y="120" width="4" height="8" fill="#2563eb" opacity="0.5" />
      <rect x="962" y="150" width="4" height="8" fill="#38bdf8" opacity="0.4" />
      <rect x="962" y="180" width="4" height="8" fill="#2563eb" opacity="0.5" />

      <rect x="1000" y="140" width="50" height="380" fill="#152238" />
      <rect x="1060" y="220" width="45" height="300" fill="#1e3354" />
      <rect x="1115" y="180" width="55" height="340" fill="#1a2d4a" />
      <rect x="1180" y="250" width="42" height="270" fill="#152238" />
      <rect x="1235" y="200" width="48" height="320" fill="#1e3354" />
      <rect x="1295" y="280" width="55" height="240" fill="#1a2d4a" />
      <rect x="1360" y="310" width="50" height="210" fill="#152238" />
      <rect x="1415" y="340" width="25" height="180" fill="#1e3354" />

      {/* Highway / Gardiner hint */}
      <path d="M0 455 L1440 455" stroke="url(#accentLine)" strokeWidth="1" opacity="0.5" />

      {/* Delivery route dots */}
      <circle cx="200" cy="448" r="3" fill="#38bdf8" opacity="0.6" />
      <circle cx="500" cy="448" r="3" fill="#2563eb" opacity="0.5" />
      <circle cx="900" cy="448" r="3" fill="#38bdf8" opacity="0.6" />
      <circle cx="1200" cy="448" r="3" fill="#2563eb" opacity="0.5" />

      <rect x="0" y="0" width="1440" height="520" fill="url(#skyGrad)" />
    </svg>
  );
}
