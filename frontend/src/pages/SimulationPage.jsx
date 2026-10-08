import { useEffect, useState } from 'react';
import { Zap, WifiOff, Wifi, Clock, AlertOctagon, BarChart2, RotateCcw, Trash2 } from 'lucide-react';
import { simulationService } from '../services/simulationService';
import { clusterService } from '../services/clusterService';
import toast from 'react-hot-toast';

const SCENARIOS = [
  {
    id: 'failure',
    icon: WifiOff,
    label: 'Simulate Failure',
    color: '#ef4444',
    description: 'Marks node as OFFLINE. Self-healing will detect and rebalance replicas.',
    action: (nodeId) => simulationService.simulateFailure(nodeId),
  },
  {
    id: 'recovery',
    icon: Wifi,
    label: 'Simulate Recovery',
    color: '#10b981',
    description: 'Restores node to ONLINE. New uploads will include this node as a candidate.',
    action: (nodeId) => simulationService.simulateRecovery(nodeId),
  },
  {
    id: 'latency',
    icon: Clock,
    label: 'Add Network Latency',
    color: '#f59e0b',
    description: 'Adds artificial 2s delay. Placement engine will deprioritize this node.',
    action: (nodeId) => simulationService.simulateNetworkDelay(nodeId, 2000),
  },
  {
    id: 'load',
    icon: BarChart2,
    label: 'High Load',
    color: '#8b5cf6',
    description: 'Simulates high CPU load. Reduces placement score for this node.',
    action: (nodeId) => simulationService.simulateHighLoad(nodeId),
  },
  {
    id: 'storage',
    icon: AlertOctagon,
    label: 'Storage Warning',
    color: '#f97316',
    description: 'Marks storage as nearly full. Node will be avoided during upload placement.',
    action: (nodeId) => simulationService.simulateStorageWarning(nodeId),
  },
];

export default function SimulationPage() {
  const [nodes, setNodes] = useState([]);
  const [simStatus, setSimStatus] = useState({});
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState('');

  const load = async () => {
    try {
      const [topo, stList] = await Promise.all([
        clusterService.getTopology(),
        simulationService.getStatus(),
      ]);
      setNodes(topo?.nodes ?? []);
      // Convert list → map keyed by node_id for easy per-node lookup
      const stMap = {};
      (Array.isArray(stList) ? stList : []).forEach(s => { stMap[s.node_id] = s; });
      setSimStatus(stMap);
    } catch {
      toast.error('Failed to load simulation data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const run = async (scenario, nodeId) => {
    const key = `${scenario.id}-${nodeId}`;
    setRunning(key);
    try {
      await scenario.action(nodeId);
      toast.success(`${scenario.label} applied to ${nodeId}`);
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || `Failed to apply ${scenario.label}`);
    } finally {
      setRunning('');
    }
  };

  const clearAll = async () => {
    try {
      await simulationService.clearAll();
      toast.success('All simulations cleared');
      await load();
    } catch {
      toast.error('Failed to clear simulations');
    }
  };

  const activeCount = Object.values(simStatus).filter(s => s?.is_simulated).length;

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <div style={{ width: 36, height: 36, borderRadius: 8, background: 'linear-gradient(135deg, #ef4444, #dc2626)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Zap size={18} color="#fff" />
            </div>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800 }}>Chaos Simulation</h1>
          </div>
          <p style={{ margin: 0, color: 'var(--clr-muted)', fontSize: 13 }}>
            Inject failure scenarios to test system resilience and self-healing
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          {activeCount > 0 && (
            <span style={{ padding: '4px 12px', borderRadius: 20, background: '#ef444422', color: '#ef4444', fontSize: 12, fontWeight: 700 }}>
              {activeCount} active simulation{activeCount > 1 ? 's' : ''}
            </span>
          )}
          <button onClick={clearAll}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, border: '1px solid #ef444455', background: 'var(--clr-surface2)', color: '#ef4444', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
            <Trash2 size={14} /> Clear All
          </button>
        </div>
      </div>

      {/* Warning banner */}
      <div style={{ background: '#f59e0b11', border: '1px solid #f59e0b33', borderRadius: 12, padding: '14px 18px', marginBottom: 28, display: 'flex', gap: 12, alignItems: 'center' }}>
        <AlertOctagon size={16} color="#f59e0b" style={{ flexShrink: 0 }} />
        <div style={{ fontSize: 13, color: '#f59e0b' }}>
          <strong>Simulation Mode</strong> — Scenarios manipulate database state only. No actual files are deleted or corrupted.
        </div>
      </div>

      {/* Node cards */}
      {loading ? (
        <div style={{ textAlign: 'center', color: 'var(--clr-muted)', padding: 60 }}>Loading nodes…</div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
          {nodes.map(node => {
            const nodeSimState = simStatus[node.node_id] || {};
            const hasActive = nodeSimState.is_simulated === true;
            const statusColor = node.status === 'ONLINE' ? '#10b981' : node.status === 'OFFLINE' ? '#ef4444' : '#f59e0b';

            return (
              <div key={node.node_id} style={{
                background: 'var(--clr-surface)', borderRadius: 16,
                border: `1px solid ${hasActive ? '#ef444444' : 'var(--clr-border)'}`,
                overflow: 'hidden',
              }}>
                {/* Node header */}
                <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--clr-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 15 }}>{node.name}</div>
                    <div style={{ fontSize: 11, color: 'var(--clr-muted)' }}>{node.node_id} · {node.host}:{node.port}</div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    {hasActive && (
                      <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: '#ef444422', color: '#ef4444', fontWeight: 700 }}>SIM ACTIVE</span>
                    )}
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: statusColor, boxShadow: `0 0 6px ${statusColor}` }} />
                    <span style={{ fontSize: 12, fontWeight: 700, color: statusColor }}>{node.status}</span>
                  </div>
                </div>

                {/* Scenarios */}
                <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {SCENARIOS.map(scenario => {
                    const key = `${scenario.id}-${node.node_id}`;
                    const isRunning = running === key;
                    const Icon = scenario.icon;
                    return (
                      <button key={scenario.id} onClick={() => run(scenario, node.node_id)} disabled={!!running}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px',
                          borderRadius: 8, border: `1px solid ${scenario.color}33`,
                          background: `${scenario.color}11`, cursor: running ? 'wait' : 'pointer',
                          textAlign: 'left', transition: 'all 0.2s', opacity: running && !isRunning ? 0.5 : 1,
                        }}
                        onMouseEnter={e => { if (!running) e.currentTarget.style.background = `${scenario.color}22`; }}
                        onMouseLeave={e => { e.currentTarget.style.background = `${scenario.color}11`; }}
                      >
                        <div style={{ width: 28, height: 28, borderRadius: 6, background: `${scenario.color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <Icon size={14} color={scenario.color} />
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: scenario.color }}>{scenario.label}</div>
                          <div style={{ fontSize: 11, color: 'var(--clr-muted)', marginTop: 1 }}>{scenario.description}</div>
                        </div>
                        {isRunning && <RotateCcw size={12} color={scenario.color} style={{ animation: 'spin 1s linear infinite' }} />}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
