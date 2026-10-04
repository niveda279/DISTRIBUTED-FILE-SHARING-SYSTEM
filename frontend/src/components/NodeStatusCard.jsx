import { Activity, HardDrive, Wifi, WifiOff } from 'lucide-react';
import { nodeService } from '../services/nodeService';

const statusColors = {
  ONLINE:   { bg: 'rgba(35,209,139,0.08)',  border: 'rgba(35,209,139,0.3)',  dot: 'var(--clr-success)' },
  OFFLINE:  { bg: 'rgba(255,77,109,0.08)',  border: 'rgba(255,77,109,0.3)',  dot: 'var(--clr-danger)' },
  DISABLED: { bg: 'rgba(124,130,163,0.08)', border: 'rgba(124,130,163,0.3)', dot: 'var(--clr-muted)' },
  UNKNOWN:  { bg: 'rgba(255,184,0,0.08)',   border: 'rgba(255,184,0,0.3)',   dot: 'var(--clr-warning)' },
};

export default function NodeStatusCard({ node }) {
  const clr = statusColors[node.status] || statusColors.UNKNOWN;
  const used = node.total_storage - node.available_storage;
  const usagePct = nodeService.usagePercent(node.total_storage, node.available_storage);

  return (
    <div className="node-card" style={{
      background: clr.bg,
      borderColor: clr.border,
    }}>
      <div className="node-header">
        <div>
          <div className="node-name">{node.name}</div>
          <div className="node-id">{node.node_id} · :{node.port}</div>
        </div>
        <span className={`badge badge-${node.status?.toLowerCase?.()}`}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: clr.dot, display: 'inline-block', marginRight: 4,
          }} />
          {node.status}
        </span>
      </div>

      {/* Storage bar */}
      {node.total_storage > 0 && (
        <div style={{ marginTop: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--clr-muted)', marginBottom: 5 }}>
            <span>{nodeService.formatStorage(used)} used</span>
            <span>{usagePct}%</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{
              width: `${usagePct}%`,
              background: usagePct > 80 ? 'var(--grad-danger)' : 'var(--grad-primary)',
            }} />
          </div>
        </div>
      )}

      <div className="node-stats">
        <div className="node-stat">
          <div className="node-stat-val" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <HardDrive size={13} color="var(--clr-primary)" />
            {node.file_count ?? 0}
          </div>
          <div className="node-stat-label">Files</div>
        </div>
        <div className="node-stat">
          <div className="node-stat-val" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Activity size={13} color="var(--clr-accent)" />
            {nodeService.formatStorage(node.available_storage)}
          </div>
          <div className="node-stat-label">Available</div>
        </div>
      </div>

      {node.last_heartbeat && (
        <div style={{ fontSize: 10, color: 'var(--clr-subtle)', marginTop: 10 }}>
          Last seen: {new Date(node.last_heartbeat).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}
