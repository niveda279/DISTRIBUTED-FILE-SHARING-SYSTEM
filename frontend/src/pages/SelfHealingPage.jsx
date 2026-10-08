import { useEffect, useState } from 'react';
import { HeartPulse, RefreshCw, Check, Clock, AlertCircle, Wrench } from 'lucide-react';
import { healingService } from '../services/healingService';
import toast from 'react-hot-toast';

const STATUS_STYLES = {
  COMPLETE:    { color: '#10b981', bg: '#10b98122', label: 'Complete' },
  COMPLETED:   { color: '#10b981', bg: '#10b98122', label: 'Completed' },
  IN_PROGRESS: { color: '#f59e0b', bg: '#f59e0b22', label: 'In Progress' },
  PENDING:     { color: '#6366f1', bg: '#6366f122', label: 'Pending' },
  FAILED:      { color: '#ef4444', bg: '#ef444422', label: 'Failed' },
};

export default function SelfHealingPage() {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [repairing, setRepairing] = useState(false);

  const load = async () => {
    try {
      const [evts, st] = await Promise.all([
        healingService.getEvents(50),
        healingService.getStatus(),
      ]);
      setEvents(Array.isArray(evts) ? evts : evts?.events ?? []);
      setStatus(st);
    } catch {
      toast.error('Failed to load healing data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); const id = setInterval(load, 8000); return () => clearInterval(id); }, []);

  const triggerRepair = async () => {
    setRepairing(true);
    try {
      const res = await healingService.triggerRepair();
      toast.success(`Healing cycle complete — ${res?.healed ?? 0} file(s) repaired`);
      await load();
    } catch {
      toast.error('Repair cycle failed');
    } finally {
      setRepairing(false);
    }
  };

  const completed = events.filter(e => e.status === 'COMPLETE' || e.status === 'COMPLETED').length;
  const failed = events.filter(e => e.status === 'FAILED').length;
  const inProgress = events.filter(e => e.status === 'IN_PROGRESS').length;

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <div style={{ width: 36, height: 36, borderRadius: 8, background: 'linear-gradient(135deg, #10b981, #059669)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <HeartPulse size={18} color="#fff" />
            </div>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800 }}>Self-Healing Monitor</h1>
          </div>
          <p style={{ margin: 0, color: 'var(--clr-muted)', fontSize: 13 }}>
            Automatic replication repair — detects and heals under-replicated files
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={load} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, border: '1px solid var(--clr-border)', background: 'var(--clr-surface2)', color: 'var(--clr-text)', cursor: 'pointer', fontSize: 13 }}>
            <RefreshCw size={14} /> Refresh
          </button>
          <button onClick={triggerRepair} disabled={repairing}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 18px', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff', cursor: repairing ? 'wait' : 'pointer', fontSize: 13, fontWeight: 600, opacity: repairing ? 0.7 : 1 }}>
            <Wrench size={14} /> {repairing ? 'Healing…' : 'Run Repair Cycle'}
          </button>
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 28 }}>
        {[
          { label: 'Total Events', value: events.length, color: '#6366f1', icon: HeartPulse },
          { label: 'Completed', value: completed, color: '#10b981', icon: Check },
          { label: 'In Progress', value: inProgress, color: '#f59e0b', icon: Clock },
          { label: 'Failed', value: failed, color: '#ef4444', icon: AlertCircle },
        ].map(({ label, value, color, icon: Icon }) => (
          <div key={label} style={{ background: 'var(--clr-surface)', border: '1px solid var(--clr-border)', borderRadius: 12, padding: '18px 20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--clr-muted)', fontWeight: 600 }}>{label}</span>
              <Icon size={14} color={color} />
            </div>
            <div style={{ fontSize: 28, fontWeight: 800, color }}>{loading ? '—' : value}</div>
          </div>
        ))}
      </div>

      {/* Status panel */}
      {status && (
        <div style={{ background: 'var(--clr-surface)', border: '1px solid var(--clr-border)', borderRadius: 16, padding: '20px 24px', marginBottom: 24 }}>
          <h2 style={{ margin: '0 0 14px', fontSize: 15, fontWeight: 700 }}>System Status</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--clr-muted)', marginBottom: 4 }}>Self-Healing Enabled</div>
              <div style={{ fontWeight: 700, color: status.healing_enabled ? '#10b981' : '#ef4444' }}>{status.healing_enabled ? 'YES' : 'NO'}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--clr-muted)', marginBottom: 4 }}>Under-Replicated Files</div>
              <div style={{ fontWeight: 700, color: status.under_replicated_files > 0 ? '#ef4444' : '#10b981' }}>{status.under_replicated_files ?? 0}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--clr-muted)', marginBottom: 4 }}>Replication Factor</div>
              <div style={{ fontWeight: 700 }}>{status.replication_factor ?? 2}</div>
            </div>
          </div>
        </div>
      )}

      {/* Events table */}
      <div style={{ background: 'var(--clr-surface)', border: '1px solid var(--clr-border)', borderRadius: 16, padding: '20px 24px' }}>
        <h2 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Healing Event Log</h2>
        {loading ? (
          <div style={{ textAlign: 'center', color: 'var(--clr-muted)', padding: 40 }}>Loading…</div>
        ) : events.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--clr-muted)', padding: 40 }}>
            <HeartPulse size={32} style={{ opacity: 0.3, marginBottom: 10 }} />
            <div>No healing events yet. System is healthy 🟢</div>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ color: 'var(--clr-muted)', fontSize: 11, textAlign: 'left' }}>
                  {['Time', 'File ID', 'From Node', 'To Node', 'Status', 'Duration'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', borderBottom: '1px solid var(--clr-border)', fontWeight: 600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {events.map((ev, i) => {
                  const st = STATUS_STYLES[ev.status] || STATUS_STYLES.PENDING;
                  return (
                    <tr key={ev.id ?? i} style={{ borderBottom: '1px solid var(--clr-border)' }}>
                      <td style={{ padding: '10px 12px', color: 'var(--clr-muted)', fontSize: 11 }}>
                        {ev.started_at ? new Date(ev.started_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                      </td>
                      <td style={{ padding: '10px 12px', fontWeight: 600 }}>#{ev.file_id}</td>
                      <td style={{ padding: '10px 12px', color: 'var(--clr-muted)' }}>{ev.source_node ?? '—'}</td>
                      <td style={{ padding: '10px 12px', color: 'var(--clr-muted)' }}>{ev.target_node ?? '—'}</td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{ padding: '2px 10px', borderRadius: 20, background: st.bg, color: st.color, fontSize: 11, fontWeight: 700 }}>
                          {st.label}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', color: 'var(--clr-muted)' }}>
                        {ev.duration_ms ? `${ev.duration_ms}ms` : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
