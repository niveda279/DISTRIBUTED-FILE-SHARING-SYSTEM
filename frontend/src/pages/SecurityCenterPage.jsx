import { useEffect, useState } from 'react';
import { Shield, AlertTriangle, AlertOctagon, Info, RefreshCw, Filter } from 'lucide-react';
import { securityService } from '../services/securityService';
import toast from 'react-hot-toast';

const RISK_STYLES = {
  HIGH: { color: '#ef4444', bg: '#ef444422', icon: AlertOctagon },
  MEDIUM: { color: '#f59e0b', bg: '#f59e0b22', icon: AlertTriangle },
  LOW: { color: '#06b6d4', bg: '#06b6d422', icon: Info },
};

export default function SecurityCenterPage() {
  const [events, setEvents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('ALL');

  const load = async () => {
    try {
      const [evts, sum] = await Promise.all([
        securityService.getEvents(),
        securityService.getSummary().catch(() => null),
      ]);
      setEvents(Array.isArray(evts) ? evts : evts?.events ?? []);
      setSummary(sum);
    } catch {
      toast.error('Failed to load security events');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); const id = setInterval(load, 30000); return () => clearInterval(id); }, []);

  const filtered = filter === 'ALL' ? events : events.filter(e => e.risk_level === filter);

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <div style={{ width: 36, height: 36, borderRadius: 8, background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Shield size={18} color="#fff" />
            </div>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800 }}>Security Center</h1>
          </div>
          <p style={{ margin: 0, color: 'var(--clr-muted)', fontSize: 13 }}>
            Behavioral anomaly detection — monitors logins, downloads, and integrity failures
          </p>
        </div>
        <button onClick={load} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, border: '1px solid var(--clr-border)', background: 'var(--clr-surface2)', color: 'var(--clr-text)', cursor: 'pointer', fontSize: 13 }}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 28 }}>
        {[
          { label: 'Total Alerts', value: events.length, color: '#8b5cf6' },
          { label: 'High Risk', value: events.filter(e => e.risk_level === 'HIGH').length, color: '#ef4444' },
          { label: 'Medium Risk', value: events.filter(e => e.risk_level === 'MEDIUM').length, color: '#f59e0b' },
          { label: 'Low Risk', value: events.filter(e => e.risk_level === 'LOW').length, color: '#06b6d4' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ background: 'var(--clr-surface)', border: '1px solid var(--clr-border)', borderRadius: 12, padding: '18px 20px' }}>
            <div style={{ fontSize: 12, color: 'var(--clr-muted)', fontWeight: 600, marginBottom: 8 }}>{label}</div>
            <div style={{ fontSize: 28, fontWeight: 800, color }}>{loading ? '—' : value}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <Filter size={15} style={{ alignSelf: 'center', color: 'var(--clr-muted)' }} />
        {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            style={{
              padding: '6px 16px', borderRadius: 20, border: '1px solid',
              borderColor: filter === f ? (RISK_STYLES[f]?.color ?? '#6366f1') : 'var(--clr-border)',
              background: filter === f ? ((RISK_STYLES[f]?.bg ?? '#6366f122')) : 'transparent',
              color: filter === f ? (RISK_STYLES[f]?.color ?? '#6366f1') : 'var(--clr-muted)',
              cursor: 'pointer', fontSize: 12, fontWeight: 600,
            }}>
            {f}
          </button>
        ))}
      </div>

      {/* Events */}
      <div style={{ background: 'var(--clr-surface)', border: '1px solid var(--clr-border)', borderRadius: 16, padding: '20px 24px' }}>
        <h2 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Security Events</h2>

        {loading ? (
          <div style={{ textAlign: 'center', color: 'var(--clr-muted)', padding: 40 }}>Loading…</div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--clr-muted)', padding: 40 }}>
            <Shield size={32} style={{ opacity: 0.3, marginBottom: 10 }} />
            <div>No security events {filter !== 'ALL' ? `with ${filter} risk` : ''} detected.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {filtered.map((ev, i) => {
              const rs = RISK_STYLES[ev.risk_level] || RISK_STYLES.LOW;
              const RiskIcon = rs.icon;
              return (
                <div key={ev.id ?? i} style={{
                  display: 'flex', gap: 14, alignItems: 'flex-start',
                  padding: '14px 16px', borderRadius: 10,
                  background: 'var(--clr-surface2)',
                  borderLeft: `3px solid ${rs.color}`,
                }}>
                  <div style={{ width: 30, height: 30, borderRadius: 8, background: rs.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <RiskIcon size={15} color={rs.color} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: 13, fontWeight: 700 }}>{ev.event_type?.replace(/_/g, ' ')}</span>
                      <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: rs.bg, color: rs.color, fontWeight: 700 }}>
                        {ev.risk_level ?? 'LOW'}
                      </span>
                    </div>
                    {ev.user_id && <div style={{ fontSize: 12, color: 'var(--clr-muted)', marginBottom: 4 }}>User ID: {ev.user_id}</div>}
                    {ev.details && (
                      <div style={{ fontSize: 11, color: 'var(--clr-subtle)', background: 'rgba(0,0,0,0.2)', borderRadius: 6, padding: '4px 8px', marginTop: 4, fontFamily: 'monospace' }}>
                        {typeof ev.details === 'string' ? ev.details : JSON.stringify(ev.details, null, 2)}
                      </div>
                    )}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--clr-muted)', whiteSpace: 'nowrap' }}>
                    {(ev.timestamp || ev.created_at) ? new Date(ev.timestamp ?? ev.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
