import { useEffect, useRef, useState } from 'react';

/**
 * SVG-based topology diagram showing master → storage nodes
 * Props: nodes = [{ node_id, name, status, storage_used_gb, storage_total_gb, avg_latency_ms, file_count, score }]
 */
export default function TopologyDiagram({ nodes = [], height = 320 }) {
  const svgRef = useRef(null);
  const [pulse, setPulse] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setPulse(p => (p + 1) % 3), 1000);
    return () => clearInterval(id);
  }, []);

  const statusColor = (s) => {
    if (s === 'ONLINE') return '#10b981';
    if (s === 'OFFLINE') return '#ef4444';
    return '#f59e0b';
  };

  const masterX = 300, masterY = 60;
  const nodePositions = [
    { x: 90, y: 230 },
    { x: 300, y: 230 },
    { x: 510, y: 230 },
  ];

  return (
    <div style={{ width: '100%', overflow: 'hidden' }}>
      <svg ref={svgRef} viewBox="0 0 600 320" width="100%" height={height} style={{ display: 'block' }}>
        <defs>
          <linearGradient id="masterGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="100%" stopColor="#8b5cf6" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* Connection lines */}
        {nodePositions.map((pos, i) => {
          const node = nodes[i];
          const color = node ? statusColor(node.status) : '#475569';
          const dashOffset = -(pulse * 8);
          return (
            <g key={i}>
              <line
                x1={masterX} y1={masterY + 36} x2={pos.x} y2={pos.y - 36}
                stroke={color} strokeWidth="1.5" strokeDasharray="8 4"
                strokeDashoffset={dashOffset} opacity="0.6"
                style={{ transition: 'stroke 0.4s' }}
              />
            </g>
          );
        })}

        {/* Master node */}
        <g filter="url(#glow)">
          <rect x={masterX - 64} y={masterY - 28} width={128} height={56} rx="12"
            fill="url(#masterGrad)" />
        </g>
        <text x={masterX} y={masterY - 4} textAnchor="middle" fill="#fff" fontSize="13" fontWeight="700">
          MASTER
        </text>
        <text x={masterX} y={masterY + 12} textAnchor="middle" fill="rgba(255,255,255,0.75)" fontSize="10">
          Coordinator
        </text>
        <circle cx={masterX + 54} cy={masterY - 18} r="6" fill="#10b981" filter="url(#glow)" />

        {/* Storage nodes */}
        {nodePositions.map((pos, i) => {
          const node = nodes[i];
          const name = node?.name || `Node ${i + 1}`;
          const status = node?.status || 'UNKNOWN';
          const color = statusColor(status);
          const usedPct = node ? Math.round((node.storage_used_gb / Math.max(node.storage_total_gb, 1)) * 100) : 0;

          return (
            <g key={i}>
              <rect x={pos.x - 72} y={pos.y - 44} width={144} height={88} rx="10"
                fill="rgba(15,23,42,0.85)" stroke={color} strokeWidth="1.5" />

              {/* Status dot */}
              <circle cx={pos.x + 56} cy={pos.y - 30} r="5" fill={color} />

              <text x={pos.x} y={pos.y - 22} textAnchor="middle" fill="#e2e8f0" fontSize="11" fontWeight="700">
                {name}
              </text>
              <text x={pos.x} y={pos.y - 6} textAnchor="middle" fill={color} fontSize="9" fontWeight="600">
                {status}
              </text>

              {/* Storage bar */}
              <rect x={pos.x - 52} y={pos.y + 4} width={104} height={6} rx="3" fill="rgba(255,255,255,0.1)" />
              <rect x={pos.x - 52} y={pos.y + 4} width={Math.max(0, 104 * usedPct / 100)} height={6} rx="3"
                fill={usedPct > 85 ? '#ef4444' : '#6366f1'} />

              <text x={pos.x - 52} y={pos.y + 24} fill="#94a3b8" fontSize="9">
                {usedPct}% used
              </text>
              <text x={pos.x + 52} y={pos.y + 24} textAnchor="end" fill="#94a3b8" fontSize="9">
                {node?.file_count ?? 0} files
              </text>

              {node?.avg_latency_ms > 0 && (
                <text x={pos.x} y={pos.y + 38} textAnchor="middle" fill="#64748b" fontSize="8">
                  {Math.round(node.avg_latency_ms)}ms
                </text>
              )}
            </g>
          );
        })}

        {/* Labels */}
        <text x={masterX} y={14} textAnchor="middle" fill="#64748b" fontSize="9" letterSpacing="0.08em">
          DISTRIBUTED FILE STORAGE TOPOLOGY
        </text>
      </svg>
    </div>
  );
}
