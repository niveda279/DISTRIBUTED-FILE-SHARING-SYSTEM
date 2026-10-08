/**
 * SVG arc gauge showing a percentage score 0–100.
 * Props: score (number), label (string), size (px)
 */
export default function ReliabilityGauge({ score = 0, label = 'Reliability', size = 180 }) {
  const r = (size / 2) * 0.7;
  const cx = size / 2;
  const cy = size / 2;
  const startAngle = -220;
  const totalDeg = 260;
  const pct = Math.min(100, Math.max(0, score));
  const valueDeg = (pct / 100) * totalDeg;

  // arc path helper
  const arc = (cx, cy, r, startDeg, endDeg) => {
    const toRad = (d) => (d * Math.PI) / 180;
    const x1 = cx + r * Math.cos(toRad(startDeg));
    const y1 = cy + r * Math.sin(toRad(startDeg));
    const x2 = cx + r * Math.cos(toRad(endDeg));
    const y2 = cy + r * Math.sin(toRad(endDeg));
    const large = endDeg - startDeg > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
  };

  const color = pct >= 80 ? '#10b981' : pct >= 60 ? '#f59e0b' : '#ef4444';
  const bgPath = arc(cx, cy, r, startAngle, startAngle + totalDeg);
  const valPath = arc(cx, cy, r, startAngle, startAngle + valueDeg);

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* Track */}
      <path d={bgPath} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="12" strokeLinecap="round" />
      {/* Value arc */}
      <path d={valPath} fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
        style={{ filter: `drop-shadow(0 0 6px ${color}88)`, transition: 'all 0.6s ease' }} />
      {/* Score */}
      <text x={cx} y={cy + 4} textAnchor="middle" fill={color} fontSize={size * 0.18} fontWeight="800">
        {Math.round(pct)}%
      </text>
      {/* Label */}
      <text x={cx} y={cy + size * 0.19} textAnchor="middle" fill="#94a3b8" fontSize={size * 0.07}>
        {label}
      </text>
    </svg>
  );
}
