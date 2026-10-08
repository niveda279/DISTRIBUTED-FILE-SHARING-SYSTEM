/**
 * Card showing per-node placement score breakdown.
 * Props: node = { name, status, score, breakdown: { storage, health, latency, load } }
 */
export default function PlacementScoreCard({ node }) {
  if (!node) return null;

  const { name, status, score, breakdown = {} } = node;
  const total = Math.round(score ?? 0);

  const statusColor = (s) => {
    if (s === 'ONLINE') return '#10b981';
    if (s === 'OFFLINE') return '#ef4444';
    return '#f59e0b';
  };

  const bars = [
    { label: 'Storage', value: breakdown.storage ?? 0, color: '#6366f1', max: 40 },
    { label: 'Health', value: breakdown.health ?? 0, color: '#10b981', max: 30 },
    { label: 'Latency', value: breakdown.latency ?? 0, color: '#06b6d4', max: 20 },
    { label: 'Load', value: breakdown.load ?? 0, color: '#f59e0b', max: 10 },
  ];

  return (
    <div style={{
      background: 'var(--clr-surface2)', borderRadius: 12, padding: '16px',
      border: `1px solid ${statusColor(status)}44`,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>{name}</div>
          <div style={{ fontSize: 11, color: statusColor(status), fontWeight: 600 }}>{status}</div>
        </div>
        <div style={{
          fontSize: 28, fontWeight: 800,
          color: total >= 70 ? '#10b981' : total >= 40 ? '#f59e0b' : '#ef4444',
        }}>
          {total}
        </div>
      </div>

      {bars.map(({ label, value, color, max }) => (
        <div key={label} style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 3 }}>
            <span style={{ color: 'var(--clr-muted)' }}>{label}</span>
            <span style={{ color, fontWeight: 600 }}>{Math.round(value)}/{max}</span>
          </div>
          <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2 }}>
            <div style={{
              width: `${Math.min(100, (value / max) * 100)}%`,
              height: '100%', background: color, borderRadius: 2,
              transition: 'width 0.5s ease',
            }} />
          </div>
        </div>
      ))}
    </div>
  );
}
