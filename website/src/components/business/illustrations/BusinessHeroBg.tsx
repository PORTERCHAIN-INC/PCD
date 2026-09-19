interface BusinessHeroBgProps {
  className?: string;
}

export default function BusinessHeroBg({ className = "" }: BusinessHeroBgProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 1440 800"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      preserveAspectRatio="xMidYMax slice"
      aria-hidden
    >
      <defs>
        <linearGradient id="nightSky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0b1a33" />
          <stop offset="60%" stopColor="#0b1220" />
          <stop offset="100%" stopColor="#060b14" />
        </linearGradient>
        <linearGradient id="blueGlow" x1="0.5" y1="0" x2="0.5" y2="1">
          <stop offset="0%" stopColor="#2563eb" stopOpacity="0.15" />
          <stop offset="100%" stopColor="#2563eb" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="buildingGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#152238" />
          <stop offset="100%" stopColor="#0b1220" />
        </linearGradient>
      </defs>

      <rect width="1440" height="800" fill="url(#nightSky)" />
      <ellipse cx="1100" cy="120" rx="400" ry="200" fill="url(#blueGlow)" />
      <ellipse cx="200" cy="200" rx="300" ry="150" fill="#2563eb" fillOpacity="0.04" />

      {/* Stars */}
      {[
        [120, 80],
        [340, 120],
        [580, 60],
        [820, 100],
        [1050, 70],
        [1280, 90],
        [200, 180],
        [450, 140],
        [700, 160],
        [950, 130],
        [1150, 150],
      ].map(([x, y], i) => (
        <circle
          key={i}
          cx={x}
          cy={y}
          r={i % 3 === 0 ? 1.5 : 1}
          fill="white"
          fillOpacity={0.3 + (i % 4) * 0.15}
        />
      ))}

      {/* Toronto skyline silhouette */}
      <path
        d="M0 520 L0 800 L1440 800 L1440 520 
           L1380 520 L1370 380 L1360 520 
           L1280 520 L1275 420 L1270 300 L1265 420 L1260 520
           L1180 520 L1175 350 L1170 200 L1165 350 L1160 520
           L1080 520 L1075 400 L1070 520
           L1000 520 L995 300 L990 520
           L920 520 L915 450 L910 520
           L840 520 L835 380 L830 520
           L760 520 L755 320 L750 180 L745 320 L740 520
           L680 520 L675 400 L670 520
           L600 520 L595 350 L590 520
           L520 520 L515 420 L510 520
           L440 520 L435 300 L430 520
           L360 520 L355 450 L350 520
           L280 520 L275 380 L270 520
           L200 520 L195 400 L190 520
           L120 520 L115 350 L110 520
           L60 520 L55 450 L50 520 L0 520 Z"
        fill="url(#buildingGrad)"
        fillOpacity="0.9"
      />

      {/* CN Tower */}
      <rect x="748" y="80" width="8" height="440" fill="#152238" />
      <ellipse cx="752" cy="80" rx="20" ry="6" fill="#1a4244" />
      <circle cx="752" cy="75" r="4" fill="#2563eb" fillOpacity="0.8" />

      {/* Building windows */}
      {Array.from({ length: 40 }).map((_, i) => {
        const x = 100 + (i % 10) * 130 + (i % 3) * 15;
        const y = 400 + Math.floor(i / 10) * 35;
        return (
          <rect
            key={i}
            x={x}
            y={y}
            width="8"
            height="12"
            fill="#2563eb"
            fillOpacity={0.15 + (i % 5) * 0.08}
            rx="1"
          />
        );
      })}

      {/* Warehouse / loading dock */}
      <rect x="0" y="580" width="500" height="220" fill="#0a1e1f" />
      <rect
        x="40"
        y="620"
        width="180"
        height="140"
        fill="#0f1b2d"
        stroke="#1a4244"
        strokeWidth="2"
      />
      <rect x="60" y="700" width="140" height="60" fill="#060b14" />
      <rect x="250" y="640" width="200" height="120" fill="#0f1b2d" rx="4" />
      <rect x="270" y="720" width="50" height="40" fill="#2563eb" fillOpacity="0.3" />
      <rect x="340" y="720" width="50" height="40" fill="#2563eb" fillOpacity="0.2" />

      {/* Delivery vans */}
      <g transform="translate(280, 690)">
        <rect x="0" y="20" width="80" height="35" rx="4" fill="#152238" />
        <rect x="60" y="28" width="25" height="27" rx="3" fill="#1a4244" />
        <circle cx="20" cy="58" r="8" fill="#060b14" />
        <circle cx="65" cy="58" r="8" fill="#060b14" />
        <rect x="5" y="25" width="50" height="3" fill="#2563eb" fillOpacity="0.6" />
      </g>
      <g transform="translate(900, 700)">
        <rect x="0" y="15" width="100" height="40" rx="4" fill="#152238" />
        <rect x="75" y="23" width="30" height="32" rx="3" fill="#1a4244" />
        <circle cx="25" cy="58" r="9" fill="#060b14" />
        <circle cx="80" cy="58" r="9" fill="#060b14" />
        <rect x="8" y="20" width="60" height="4" fill="#2563eb" fillOpacity="0.5" />
      </g>

      {/* Ground gradient */}
      <rect x="0" y="750" width="1440" height="50" fill="#060b14" fillOpacity="0.5" />
    </svg>
  );
}
