import { useEffect, useState, useRef } from 'react';
import { Network, RefreshCw, Wifi, WifiOff, AlertTriangle, Activity } from 'lucide-react';
import { clusterService } from '../services/clusterService';
import TopologyDiagram from '../components/TopologyDiagram';
import PlacementScoreCard from '../components/PlacementScoreCard';
import toast from 'react-hot-toast';

const STATUS_COLOR = { ONLINE: '#10b981', OFFLINE: '#ef4444', DEGRADED: '#f59e0b', UNKNOWN: '#64748b' };

export default function ClusterTopologyPage() {
  const [topology, setTopology] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const evtSourceRef = useRef(null);

  const load = async () => {
    try {
      const [topo, evts] = await Promise.all([
        clusterService.getTopology(),
        clusterService.getEvents(20),
      ]);
      setTopology(topo);
      setEvents(Array.isArray(evts) ? evts : evts?.events ?? []);
      setLastUpdated(new Date());
    } catch (e) {
      toast.error('Failed to load topology');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);

  const rawNodes = topology?.nodes ?? [];

  // Normalize to uniform shape for components
  const nodes = rawNodes.map(n => ({
    ...n,
    name: n.name ?? n.node_name,
    score: n.final_score ?? n.score ?? 0,
    storage_used_gb: n.total_storage > 0 ? ((n.total_storage - n.available_storage) / 1e9) : 0,
    storage_total_gb: n.total_storage ? (n.total_storage / 1e9) : 0,
    breakdown: {
      storage: n.storage_score ?? 0,
      health: n.health_score ?? 0,
      latency: n.latency_score ?? 0,
      load: n.load_score ?? 0,
    },
  }));

  const online = nodes.filter(n => n.status === 'ONLINE').length;
  const offline = nodes.filter(n => n.status === 'OFFLINE').length;
  const totalFiles = (topology?.cluster_summary?.total_files) ?? nodes.reduce((s, n) => s + (n.file_count ?? 0), 0);

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <div style={{ width: 36, height: 36, borderRadius: 8, background: 'var(--grad-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Network size={18} color="#fff" />
            </div>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800 }}>Cluster Topology</h1>
          </div>
          <p style={{ margin: 0, color: 'var(--clr-muted)', fontSize: 13 }}>
            Live distributed node map with real-time placement scores
          </p>
        </div>
        <button
          onClick={load}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, border: '1px solid var(--clr-border)', background: 'var(--clr-surface2)', color: 'var(--clr-text)', cursor: 'pointer', fontSize: 13 }}
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 28 }}>
        {[
          { label: 'Total Nodes', value: nodes.length, icon: Network, color: '#6366f1' },
          { label: 'Online', value: online, icon: Wifi, color: '#10b981' },
          { label: 'Offline', value: offline, icon: WifiOff, color: '#ef4444' },
          { label: 'Total Files', value: totalFiles, icon: Activity, color: '#06b6d4' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} style={{ background: 'var(--clr-surface)', border: '1px solid var(--clr-border)', borderRadius: 12, padding: '18px 20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--clr-muted)', fontWeight: 600 }}>{label}</span>
              <div style={{ width: 28, height: 28, borderRadius: 6, background: `${color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icon size={14} color={color} />
              </div>
            </div>
            <div style={{ fontSize: 28, fontWeight: 800, color }}>{loading ? '—' : value}</div>
          </div>
        ))}
      </div>

      {/* Topology SVG */}
      <div style={{ background: 'var(--clr-surface)', border: '1px solid var(--clr-border)', borderRadius: 16, padding: '24px', marginBottom: 28 }}>
        <h2 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 700 }}>Network Map</h2>
        {loading ? (
          <div style={{ textAlign: 'center', color: 'var(--clr-muted)', padding: 60 }}>Loading topology…</div>
        ) : (
          <TopologyDiagram nodes={nodes} />
        )}
        {lastUpdated && (
          <div style={{ textAlign: 'right', fontSize: 11, color: 'var(--clr-muted)', marginTop: 8 }}>
            Last updated: {lastUpdated.toLocaleTimeString()}
          </div>
        )}
      </div>

      {/* Placement scores */}
      <div style={{ marginBottom: 28 }}>
        <h2 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 700 }}>Placement Score Breakdown</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {loading
            ? [1, 2, 3].map(i => <div key={i} style={{ background: 'var(--clr-surface)', borderRadius: 12, height: 160 }} />)
            : nodes.map(n => <PlacementScoreCard key={n.node_id} node={n} />)
          }
        </div>
      </div>

      {/* Recent events */}
      <div style={{ background: 'var(--clr-surface)', border: '1px solid var(--clr-border)', borderRadius: 16, padding: '24px' }}>
        <h2 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 700 }}>Recent System Events</h2>
        {events.length === 0 ? (
          <div style={{ color: 'var(--clr-muted)', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>No events recorded yet.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 280, overflowY: 'auto' }}>
            {events.map((ev, i) => {
              const sev = ev.severity?.toUpperCase();
              const color = sev === 'HIGH' ? '#ef4444' : sev === 'MEDIUM' ? '#f59e0b' : '#6366f1';
              return (
                <div key={ev.id ?? i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: '10px 14px', background: 'var(--clr-surface2)', borderRadius: 8, borderLeft: `2px solid ${color}` }}>
                  <AlertTriangle size={13} color={color} style={{ flexShrink: 0, marginTop: 1 }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color }}>{ev.event_type}</div>
                    <div style={{ fontSize: 11, color: 'var(--clr-muted)' }}>{ev.message || JSON.stringify(ev.payload ?? {})}</div>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--clr-subtle)', whiteSpace: 'nowrap' }}>
                    {(ev.timestamp || ev.created_at) ? new Date(ev.timestamp ?? ev.created_at).toLocaleTimeString() : ''}
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
