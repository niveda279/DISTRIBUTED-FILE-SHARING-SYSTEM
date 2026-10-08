import { useEffect, useState } from 'react';
import { BarChart2, RefreshCw, HardDrive, TrendingUp, Copy, Server } from 'lucide-react';
import { analyticsService } from '../services/analyticsService';
import { clusterService } from '../services/clusterService';
import ReliabilityGauge from '../components/ReliabilityGauge';
import toast from 'react-hot-toast';

function MiniBarChart({ data = [], colorFn }) {
  const max = Math.max(...data.map(d => d.value), 1);
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 80 }}>
      {data.map((d, i) => (
        <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
          <div style={{
            width: '100%', borderRadius: '4px 4px 0 0',
            height: `${Math.max(4, (d.value / max) * 70)}px`,
            background: colorFn ? colorFn(d) : 'var(--grad-primary)',
            transition: 'height 0.5s ease',
          }} />
          <div style={{ fontSize: 9, color: 'var(--clr-muted)', textAlign: 'center', lineHeight: 1.2 }}>{d.label}</div>
        </div>
      ))}
    </div>
  );
}

export default function StorageAnalyticsPage() {
  const [stats, setStats] = useState(null);
  const [reliability, setReliability] = useState(null);
  const [nodeMetrics, setNodeMetrics] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [extended, basicStats, rel, topo] = await Promise.all([
        analyticsService.getExtendedStats().catch(() => null),
        import('../services/api').then(m => m.default.get('/api/admin/stats').then(r => r.data)).catch(() => null),
        analyticsService.getReliability().catch(() => null),
        clusterService.getTopology().catch(() => null),
      ]);
      // Build a flat stats object from extended + basic stats
      const dedup = extended?.deduplication ?? {};
      const logicalBytes = dedup.total_logical_bytes ?? 0;
      const savedBytes = dedup.bytes_saved ?? 0;
      const st = {
        total_files: basicStats?.total_files ?? 0,
        total_storage_used_bytes: basicStats?.total_size_bytes ?? 0,
        dedup_bytes_saved: savedBytes,
        dedup_files: dedup.deduplicated_file_count ?? 0,
        dedup_percentage: logicalBytes > 0 ? (savedBytes / logicalBytes) * 100 : 0,
        total_healing_events: (extended?.healing?.total_healed ?? 0) + (extended?.healing?.total_failed ?? 0),
      };
      setStats(st);
      setReliability(rel);
      const rawNodes = topo?.nodes ?? [];
      setNodeMetrics(rawNodes.map(n => ({
        ...n,
        name: n.name ?? n.node_name,
        score: n.final_score ?? n.score,
        storage_used_gb: n.total_storage > 0 ? (n.total_storage - n.available_storage) / 1e9 : 0,
        storage_total_gb: n.total_storage ? n.total_storage / 1e9 : 0,
      })));
    } catch {
      toast.error('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); const id = setInterval(load, 15000); return () => clearInterval(id); }, []);

  const fmt = (bytes) => {
    if (!bytes) return '0 B';
    const u = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${u[i]}`;
  };

  const storageBarData = nodeMetrics.map(n => ({
    label: n.name?.replace('Storage Node ', 'N'),
    value: n.storage_used_gb ?? 0,
    pct: n.storage_total_gb > 0 ? (n.storage_used_gb / n.storage_total_gb) * 100 : 0,
  }));

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <div style={{ width: 36, height: 36, borderRadius: 8, background: 'linear-gradient(135deg, #06b6d4, #0891b2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <BarChart2 size={18} color="#fff" />
            </div>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800 }}>Storage Analytics</h1>
          </div>
          <p style={{ margin: 0, color: 'var(--clr-muted)', fontSize: 13 }}>
            System reliability, storage utilization, and deduplication savings
          </p>
        </div>
        <button onClick={load} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, border: '1px solid var(--clr-border)', background: 'var(--clr-surface2)', color: 'var(--clr-text)', cursor: 'pointer', fontSize: 13 }}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Top row: Reliability gauge + stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 24, marginBottom: 24 }}>
        {/* Gauge */}
        <div style={{ background: 'var(--clr-surface)', border: '1px solid var(--clr-border)', borderRadius: 16, padding: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minWidth: 220 }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>System Reliability</div>
          <ReliabilityGauge score={reliability?.score ?? 0} label="Score" size={160} />
          {reliability && (
            <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 6, width: '100%' }}>
              {[
                { label: 'Node Availability', value: reliability.breakdown?.node_availability },
                { label: 'Replication Health', value: reliability.breakdown?.replication_health },
                { label: 'Storage Health', value: reliability.breakdown?.storage_health },
                { label: 'Integrity', value: reliability.breakdown?.integrity_health },
              ].map(({ label, value }) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                  <span style={{ color: 'var(--clr-muted)' }}>{label}</span>
                  <span style={{ fontWeight: 700, color: value >= 80 ? '#10b981' : value >= 60 ? '#f59e0b' : '#ef4444' }}>
                    {value != null ? `${Math.round(value)}%` : '—'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
          {[
            { label: 'Total Files', value: stats?.total_files ?? nodeMetrics.reduce((s, n) => s + (n.file_count ?? 0), 0), icon: HardDrive, color: '#6366f1' },
            { label: 'Total Storage Used', value: fmt((stats?.total_storage_used_bytes) ?? nodeMetrics.reduce((s, n) => s + (n.storage_used_gb ?? 0) * 1e9, 0)), icon: Server, color: '#06b6d4' },
            { label: 'Dedup Savings', value: fmt(stats?.dedup_bytes_saved ?? 0), icon: Copy, color: '#10b981' },
            { label: 'Healing Events', value: stats?.total_healing_events ?? 0, icon: TrendingUp, color: '#f59e0b' },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} style={{ background: 'var(--clr-surface)', border: '1px solid var(--clr-border)', borderRadius: 12, padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span style={{ fontSize: 12, color: 'var(--clr-muted)', fontWeight: 600 }}>{label}</span>
                <div style={{ width: 28, height: 28, borderRadius: 6, background: `${color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Icon size={13} color={color} />
                </div>
              </div>
              <div style={{ fontSize: 22, fontWeight: 800, color }}>{loading ? '—' : value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Storage per node bars */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
        <div style={{ background: 'var(--clr-surface)', border: '1px solid var(--clr-border)', borderRadius: 16, padding: '20px 24px' }}>
          <h2 style={{ margin: '0 0 20px', fontSize: 15, fontWeight: 700 }}>Storage Utilization per Node</h2>
          {loading ? <div style={{ color: 'var(--clr-muted)', padding: 20 }}>Loading…</div> : (
            <>
              <MiniBarChart
                data={storageBarData}
                colorFn={(d) => d.pct > 85 ? '#ef4444' : d.pct > 65 ? '#f59e0b' : '#6366f1'}
              />
              <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {nodeMetrics.map(n => {
                  const pct = n.storage_total_gb > 0 ? (n.storage_used_gb / n.storage_total_gb) * 100 : 0;
                  const color = pct > 85 ? '#ef4444' : pct > 65 ? '#f59e0b' : '#10b981';
                  return (
                    <div key={n.node_id}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
                        <span style={{ color: 'var(--clr-muted)' }}>{n.name}</span>
                        <span style={{ color, fontWeight: 700 }}>{Math.round(pct)}%</span>
                      </div>
                      <div style={{ height: 5, background: 'rgba(255,255,255,0.06)', borderRadius: 3 }}>
                        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3, transition: 'width 0.5s' }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>

        {/* Per-node details table */}
        <div style={{ background: 'var(--clr-surface)', border: '1px solid var(--clr-border)', borderRadius: 16, padding: '20px 24px' }}>
          <h2 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Node Details</h2>
          {loading ? <div style={{ color: 'var(--clr-muted)', padding: 20 }}>Loading…</div> : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ color: 'var(--clr-muted)', fontSize: 11 }}>
                  {['Node', 'Status', 'Files', 'Latency', 'Score'].map(h => (
                    <th key={h} style={{ padding: '6px 10px', borderBottom: '1px solid var(--clr-border)', textAlign: 'left', fontWeight: 600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {nodeMetrics.map(n => {
                  const statusColor = n.status === 'ONLINE' ? '#10b981' : n.status === 'OFFLINE' ? '#ef4444' : '#f59e0b';
                  return (
                    <tr key={n.node_id} style={{ borderBottom: '1px solid var(--clr-border)' }}>
                      <td style={{ padding: '10px 10px', fontWeight: 600 }}>{n.name?.replace('Storage Node ', 'N')}</td>
                      <td style={{ padding: '10px 10px' }}>
                        <span style={{ color: statusColor, fontWeight: 700, fontSize: 11 }}>{n.status}</span>
                      </td>
                      <td style={{ padding: '10px 10px', color: 'var(--clr-muted)' }}>{n.file_count ?? 0}</td>
                      <td style={{ padding: '10px 10px', color: 'var(--clr-muted)' }}>{n.avg_latency_ms ? `${Math.round(n.avg_latency_ms)}ms` : '—'}</td>
                      <td style={{ padding: '10px 10px', fontWeight: 700, color: (n.score ?? 0) >= 70 ? '#10b981' : '#f59e0b' }}>
                        {n.score != null ? Math.round(n.score) : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Deduplication panel */}
      {stats?.dedup_bytes_saved > 0 && (
        <div style={{ background: 'linear-gradient(135deg, #10b98111, #059669011)', border: '1px solid #10b98133', borderRadius: 16, padding: '20px 24px' }}>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <Copy size={28} color="#10b981" />
            <div>
              <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>Deduplication Savings</div>
              <div style={{ color: 'var(--clr-muted)', fontSize: 13 }}>
                <strong style={{ color: '#10b981' }}>{fmt(stats.dedup_bytes_saved)}</strong> saved across{' '}
                <strong style={{ color: '#10b981' }}>{stats.dedup_files ?? 0}</strong> deduplicated file(s).
                Physical storage reduced by{' '}
                <strong style={{ color: '#10b981' }}>{stats.dedup_percentage?.toFixed(1) ?? 0}%</strong>.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
