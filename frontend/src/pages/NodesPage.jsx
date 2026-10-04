import { useEffect, useState } from 'react';
import { Server, RefreshCw, Activity, Power, PowerOff } from 'lucide-react';
import Navbar from '../components/Navbar';
import NodeStatusCard from '../components/NodeStatusCard';
import { nodeService } from '../services/nodeService';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

export default function NodesPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pinging, setPinging] = useState({});
  const [toggling, setToggling] = useState({});

  const load = async () => {
    setLoading(true);
    try { setNodes(await nodeService.list()); }
    catch { toast.error('Failed to load nodes'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const ping = async (nodeId) => {
    setPinging(p => ({ ...p, [nodeId]: true }));
    try {
      const res = await nodeService.ping(nodeId);
      toast.success(`${nodeId}: ${res.online ? '✓ Online' : '✗ Offline'}`);
      load();
    } catch {
      toast.error(`Ping failed for ${nodeId}`);
    } finally {
      setPinging(p => ({ ...p, [nodeId]: false }));
    }
  };

  const toggle = async (node) => {
    setToggling(t => ({ ...t, [node.node_id]: true }));
    try {
      if (node.status === 'DISABLED') {
        await nodeService.enable(node.node_id);
        toast.success(`${node.node_id} enabled`);
      } else {
        await nodeService.disable(node.node_id);
        toast.success(`${node.node_id} disabled`);
      }
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally {
      setToggling(t => ({ ...t, [node.node_id]: false }));
    }
  };

  const online = nodes.filter(n => n.status === 'ONLINE').length;
  const totalFiles = nodes.reduce((s, n) => s + (n.file_count || 0), 0);
  const totalAvail = nodes.reduce((s, n) => s + (n.available_storage || 0), 0);

  return (
    <>
      <Navbar
        title="Storage Nodes"
        subtitle={`${online}/${nodes.length} online · ${totalFiles} files · ${nodeService.formatStorage(totalAvail)} available`}
      />
      <div className="page-inner fade-in">
        {/* Summary bar */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 24, justifyContent: 'flex-end' }}>
          <button className="btn btn-ghost" onClick={load} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
            Refresh
          </button>
        </div>

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
            <div className="spinner" />
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
            {nodes.map(node => (
              <div key={node.node_id}>
                <NodeStatusCard node={node} />
                <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => ping(node.node_id)}
                    disabled={pinging[node.node_id]}
                    style={{ flex: 1 }}
                  >
                    <Activity size={13} className={pinging[node.node_id] ? 'spin' : ''} />
                    Ping
                  </button>
                  {isAdmin && (
                    <button
                      className={`btn btn-sm ${node.status === 'DISABLED' ? 'btn-primary' : 'btn-ghost'}`}
                      onClick={() => toggle(node)}
                      disabled={toggling[node.node_id]}
                      style={{
                        flex: 1,
                        color: node.status !== 'DISABLED' ? 'var(--clr-danger)' : undefined,
                        borderColor: node.status !== 'DISABLED' ? 'var(--clr-danger)' : undefined,
                      }}
                    >
                      {node.status === 'DISABLED'
                        ? <><Power size={13} />Enable</>
                        : <><PowerOff size={13} />Disable</>
                      }
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Raw health table */}
        {!loading && nodes.length > 0 && (
          <div className="card" style={{ marginTop: 28, padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--clr-border)', fontWeight: 700, fontSize: 15, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Server size={16} color="var(--clr-muted)" />
              Node Summary
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Node ID</th>
                    <th>Host</th>
                    <th>Port</th>
                    <th>Status</th>
                    <th>Files</th>
                    <th>Available</th>
                    <th>Last Heartbeat</th>
                  </tr>
                </thead>
                <tbody>
                  {nodes.map(n => (
                    <tr key={n.node_id}>
                      <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{n.node_id}</td>
                      <td style={{ color: 'var(--clr-muted)' }}>{n.host}</td>
                      <td style={{ color: 'var(--clr-muted)' }}>{n.port}</td>
                      <td>
                        <span className={`badge badge-${n.status?.toLowerCase?.()}`}>
                          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor', display: 'inline-block', marginRight: 5 }} />
                          {n.status}
                        </span>
                      </td>
                      <td>{n.file_count ?? 0}</td>
                      <td>{nodeService.formatStorage(n.available_storage)}</td>
                      <td style={{ fontSize: 12, color: 'var(--clr-muted)' }}>
                        {n.last_heartbeat ? new Date(n.last_heartbeat).toLocaleTimeString() : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
