import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, History, MapPin, Share2, Shield, Clock, RefreshCw, RotateCcw } from 'lucide-react';
import { fileService } from '../services/fileService';
import ActivityTimeline from '../components/ActivityTimeline';
import toast from 'react-hot-toast';

const STATUS_COLOR = { ONLINE: '#10b981', OFFLINE: '#ef4444', DEGRADED: '#f59e0b', UNKNOWN: '#64748b' };

export default function FileDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [file, setFile] = useState(null);
  const [versions, setVersions] = useState([]);
  const [activity, setActivity] = useState([]);
  const [replicas, setReplicas] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [f, v, a, r] = await Promise.all([
        fileService.getById(id),
        fileService.getVersions(id).catch(() => []),
        fileService.getActivity(id).catch(() => []),
        fileService.getReplicas(id).catch(() => []),
      ]);
      setFile(f);
      setVersions(Array.isArray(v) ? v : v?.versions ?? []);
      setActivity(Array.isArray(a) ? a : a?.events ?? []);
      setReplicas(Array.isArray(r) ? r : r?.replicas ?? []);
    } catch {
      toast.error('Failed to load file details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (id) load(); }, [id]);

  const fmt = fileService.formatSize;
  const fmtDate = (d) => d ? new Date(d).toLocaleString() : '—';

  const handleDownload = () => {
    fileService.download(id, file?.original_filename);
  };  

  const handleRestoreVersion = async (versionId) => {
    try {
      await fileService.restoreVersion(id, versionId);
      toast.success('Version restored successfully');
      load();
    } catch {
      toast.error('Failed to restore version');
    }
  };

  if (loading) return (
    <div style={{ padding: 40, textAlign: 'center', color: 'var(--clr-muted)' }}>Loading file details…</div>
  );

  if (!file) return (
    <div style={{ padding: 40, textAlign: 'center', color: 'var(--clr-muted)' }}>File not found.</div>
  );

  const TABS = [
    { id: 'overview', label: 'Overview', icon: Shield },
    { id: 'versions', label: `Versions (${versions.length})`, icon: History },
    { id: 'replicas', label: `Replicas (${replicas.length})`, icon: MapPin },
    { id: 'activity', label: 'Activity', icon: Clock },
  ];

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1000 }}>
      {/* Back */}
      <button onClick={() => navigate(-1)}
        style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', color: 'var(--clr-muted)', cursor: 'pointer', fontSize: 13, marginBottom: 20, padding: 0 }}>
        <ArrowLeft size={15} /> Back
      </button>

      {/* File header */}
      <div style={{ background: 'var(--clr-surface)', border: '1px solid var(--clr-border)', borderRadius: 16, padding: '24px', marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <h1 style={{ margin: '0 0 6px', fontSize: 20, fontWeight: 800, wordBreak: 'break-all' }}>
              {file.original_filename}
            </h1>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, color: 'var(--clr-muted)' }}>{fmt(file.size)}</span>
              <span style={{ fontSize: 12, color: 'var(--clr-muted)' }}>{file.mime_type || 'Unknown type'}</span>
              <span style={{ fontSize: 12, color: 'var(--clr-muted)' }}>v{file.version_number ?? 1}</span>
              <span style={{ fontSize: 12, color: 'var(--clr-muted)' }}>{fmtDate(file.created_at)}</span>
              {file.is_deduplicated && (
                <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 10, background: '#10b98122', color: '#10b981', fontWeight: 700 }}>
                  DEDUPLICATED
                </span>
              )}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, flexShrink: 0 }}>
            <button onClick={load} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8, border: '1px solid var(--clr-border)', background: 'var(--clr-surface2)', color: 'var(--clr-text)', cursor: 'pointer', fontSize: 12 }}>
              <RefreshCw size={13} /> Refresh
            </button>
            <button onClick={handleDownload} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, border: 'none', background: 'var(--grad-primary)', color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
              <Download size={14} /> Download
            </button>
          </div>
        </div>

        {/* Checksum */}
        <div style={{ marginTop: 14, padding: '10px 14px', background: 'var(--clr-surface2)', borderRadius: 8 }}>
          <span style={{ fontSize: 11, color: 'var(--clr-muted)' }}>SHA-256: </span>
          <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--clr-text)', wordBreak: 'break-all' }}>{file.checksum}</span>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, background: 'var(--clr-surface)', borderRadius: 10, padding: 4, border: '1px solid var(--clr-border)' }}>
        {TABS.map(({ id: t, label, icon: Icon }) => (
          <button key={t} onClick={() => setActiveTab(t)}
            style={{
              flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              padding: '8px 12px', borderRadius: 7, border: 'none',
              background: activeTab === t ? 'var(--grad-primary)' : 'transparent',
              color: activeTab === t ? '#fff' : 'var(--clr-muted)',
              cursor: 'pointer', fontSize: 12, fontWeight: activeTab === t ? 700 : 500,
              transition: 'all 0.15s',
            }}>
            <Icon size={13} /> {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ background: 'var(--clr-surface)', border: '1px solid var(--clr-border)', borderRadius: 16, padding: '24px' }}>

        {/* OVERVIEW */}
        {activeTab === 'overview' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            {[
              ['File Name', file.original_filename],
              ['Physical ID', file.filename],
              ['Size', fmt(file.size)],
              ['MIME Type', file.mime_type || '—'],
              ['Owner', file.owner_id],
              ['Version', `v${file.version_number ?? 1}`],
              ['Is Deduplicated', file.is_deduplicated ? 'Yes' : 'No'],
              ['Access Count', file.access_count ?? 0],
              ['Created', fmtDate(file.created_at)],
              ['Last Modified', fmtDate(file.updated_at)],
              ['Last Accessed', fmtDate(file.last_accessed_at)],
              ['Primary Node', file.primary_node_id ?? '—'],
            ].map(([k, v]) => (
              <div key={k}>
                <div style={{ fontSize: 11, color: 'var(--clr-muted)', fontWeight: 600, marginBottom: 4 }}>{k}</div>
                <div style={{ fontSize: 13, wordBreak: 'break-all' }}>{v}</div>
              </div>
            ))}
          </div>
        )}

        {/* VERSIONS */}
        {activeTab === 'versions' && (
          <div>
            {versions.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--clr-muted)', padding: 30 }}>No version history found.</div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ color: 'var(--clr-muted)', fontSize: 11 }}>
                    {['Version', 'Size', 'Created', 'Current', 'Actions'].map(h => (
                      <th key={h} style={{ padding: '8px 12px', borderBottom: '1px solid var(--clr-border)', textAlign: 'left', fontWeight: 600 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {versions.map(v => (
                    <tr key={v.id} style={{ borderBottom: '1px solid var(--clr-border)' }}>
                      <td style={{ padding: '10px 12px', fontWeight: 700 }}>v{v.version_number}</td>
                      <td style={{ padding: '10px 12px', color: 'var(--clr-muted)' }}>{fmt(v.size ?? 0)}</td>
                      <td style={{ padding: '10px 12px', color: 'var(--clr-muted)', fontSize: 11 }}>{fmtDate(v.created_at)}</td>
                      <td style={{ padding: '10px 12px' }}>
                        {v.is_current_version ? (
                          <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 10, background: '#10b98122', color: '#10b981', fontWeight: 700 }}>CURRENT</span>
                        ) : '—'}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <div style={{ display: 'flex', gap: 8 }}>
                          <button onClick={() => fileService.downloadVersion(id, v.id, `v${v.version_number}_${file.original_filename}`)}
                            style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', borderRadius: 6, border: '1px solid var(--clr-border)', background: 'transparent', color: 'var(--clr-muted)', cursor: 'pointer', fontSize: 11 }}>
                            <Download size={11} /> Download
                          </button>
                          {!v.is_current_version && (
                            <button onClick={() => handleRestoreVersion(v.id)}
                              style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', borderRadius: 6, border: 'none', background: '#6366f122', color: '#6366f1', cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                              <RotateCcw size={11} /> Restore
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* REPLICAS */}
        {activeTab === 'replicas' && (
          <div>
            {replicas.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--clr-muted)', padding: 30 }}>No replica locations found.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {replicas.map((r, i) => {
                  const color = STATUS_COLOR[r.node_status ?? 'UNKNOWN'];
                  return (
                    <div key={r.id ?? i} style={{ display: 'flex', gap: 14, alignItems: 'center', padding: '14px 16px', background: 'var(--clr-surface2)', borderRadius: 10, borderLeft: `3px solid ${color}` }}>
                      <MapPin size={16} color={color} style={{ flexShrink: 0 }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 700, fontSize: 13 }}>{r.node_name ?? r.node_id}</div>
                        <div style={{ fontSize: 11, color: 'var(--clr-muted)' }}>{r.node_id} · Stored: {fmtDate(r.stored_at)}</div>
                        {r.physical_path && <div style={{ fontSize: 11, color: 'var(--clr-subtle)', fontFamily: 'monospace', marginTop: 2 }}>{r.physical_path}</div>}
                      </div>
                      <span style={{ fontSize: 11, padding: '2px 10px', borderRadius: 10, background: `${color}22`, color, fontWeight: 700 }}>
                        {r.node_status ?? 'UNKNOWN'}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ACTIVITY */}
        {activeTab === 'activity' && (
          <ActivityTimeline events={activity} />
        )}
      </div>
    </div>
  );
}
