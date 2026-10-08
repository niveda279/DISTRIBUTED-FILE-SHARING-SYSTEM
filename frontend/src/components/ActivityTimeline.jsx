/**
 * Vertical timeline for file audit events.
 * Props: events = [{ id, action, created_at, user_name?, details? }]
 */
export default function ActivityTimeline({ events = [] }) {
  const actionColor = (action) => {
    if (!action) return '#6366f1';
    const a = action.toUpperCase();
    if (a.includes('UPLOAD') || a.includes('CREATE')) return '#10b981';
    if (a.includes('DELETE')) return '#ef4444';
    if (a.includes('DOWNLOAD')) return '#6366f1';
    if (a.includes('SHARE')) return '#f59e0b';
    if (a.includes('HEAL') || a.includes('REPLICATE')) return '#06b6d4';
    if (a.includes('FAIL') || a.includes('ERROR')) return '#ef4444';
    return '#8b5cf6';
  };

  const fmt = (dt) => {
    if (!dt) return '';
    try {
      return new Date(dt).toLocaleString(undefined, {
        month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    } catch {
      return dt;
    }
  };

  if (!events.length) {
    return (
      <div style={{ color: 'var(--clr-muted)', fontSize: 13, textAlign: 'center', padding: '24px 0' }}>
        No activity recorded yet.
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', paddingLeft: 28 }}>
      {/* Vertical line */}
      <div style={{
        position: 'absolute', left: 10, top: 0, bottom: 0,
        width: 2, background: 'var(--clr-border)',
      }} />

      {events.map((ev, i) => {
        const color = actionColor(ev.action || ev.event_type);
        return (
          <div key={ev.id ?? i} style={{ position: 'relative', marginBottom: 20 }}>
            {/* Dot */}
            <div style={{
              position: 'absolute', left: -23, top: 3,
              width: 12, height: 12, borderRadius: '50%',
              background: color, border: '2px solid var(--clr-bg)',
              boxShadow: `0 0 6px ${color}66`,
            }} />

            <div style={{
              background: 'var(--clr-surface2)',
              borderRadius: 8, padding: '10px 14px',
              borderLeft: `2px solid ${color}`,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 12, fontWeight: 700, color }}>
                  {ev.action || ev.event_type || 'EVENT'}
                </span>
                <span style={{ fontSize: 11, color: 'var(--clr-muted)' }}>{fmt(ev.created_at)}</span>
              </div>
              {ev.user_name && (
                <div style={{ fontSize: 11, color: 'var(--clr-muted)' }}>by {ev.user_name}</div>
              )}
              {ev.details && (
                <div style={{ fontSize: 11, color: 'var(--clr-subtle)', marginTop: 4, wordBreak: 'break-all' }}>
                  {typeof ev.details === 'string' ? ev.details : JSON.stringify(ev.details)}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
