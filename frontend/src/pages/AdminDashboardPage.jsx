import { useEffect, useState } from 'react';
import {
  Users, FileText, Server, TrendingUp, RefreshCw,
  UserCheck, UserX, ShieldCheck, Activity,
} from 'lucide-react';
import Navbar from '../components/Navbar';
import { adminService } from '../services/adminService';
import toast from 'react-hot-toast';

function StatCard({ icon: Icon, label, value, colorClass }) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${colorClass}`}><Icon size={22} /></div>
      <div>
        <div className="stat-value">{value ?? '—'}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}

export default function AdminDashboardPage() {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [logs, setLogs] = useState([]);
  const [tab, setTab] = useState('users'); // users | logs
  const [loading, setLoading] = useState(true);
  const [actionId, setActionId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [s, u, l] = await Promise.all([
        adminService.getStats(),
        adminService.listUsers(),
        adminService.auditLogs(),
      ]);
      setStats(s);
      setUsers(u);
      setLogs(l);
    } catch {
      toast.error('Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const toggleUser = async (user) => {
    setActionId(user.id);
    try {
      const updated = user.is_active
        ? await adminService.disableUser(user.id)
        : await adminService.enableUser(user.id);
      setUsers(u => u.map(x => x.id === user.id ? updated : x));
      toast.success(`User ${updated.is_active ? 'enabled' : 'disabled'}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally {
      setActionId(null);
    }
  };

  const promote = async (user) => {
    if (!confirm(`Promote ${user.email} to ADMIN?`)) return;
    setActionId(user.id);
    try {
      const updated = await adminService.promoteUser(user.id);
      setUsers(u => u.map(x => x.id === user.id ? updated : x));
      toast.success(`${user.name} is now an admin`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally {
      setActionId(null);
    }
  };

  const actionColors = {
    REGISTER: 'var(--clr-success)',
    LOGIN:     'var(--clr-primary)',
    UPLOAD:    'var(--clr-accent)',
    DOWNLOAD:  'var(--clr-warning)',
    DELETE:    'var(--clr-danger)',
    SHARE:     'var(--clr-accent2)',
    UNSHARE:   'var(--clr-muted)',
  };

  return (
    <>
      <Navbar title="Admin Dashboard" subtitle="System management and monitoring" />
      <div className="page-inner fade-in">
        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px,1fr))', gap: 16, marginBottom: 28 }}>
          <StatCard icon={Users}      label="Total Users"   value={stats?.total_users}        colorClass="stat-icon-blue" />
          <StatCard icon={FileText}   label="Total Files"   value={stats?.total_files}        colorClass="stat-icon-green" />
          <StatCard icon={TrendingUp} label="Storage Used"  value={stats ? `${Math.round(stats.total_size_bytes / 1024 / 1024)} MB` : null} colorClass="stat-icon-yellow" />
          <StatCard icon={Server}     label="Nodes Online"  value={stats ? `${stats.online_nodes}/${stats.total_nodes}` : null} colorClass="stat-icon-pink" />
        </div>

        {/* Tab + Refresh */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: 4, background: 'var(--clr-surface)', borderRadius: 10, padding: 4, border: '1px solid var(--clr-border)' }}>
            {[['users', 'Users', Users], ['logs', 'Audit Logs', Activity]].map(([id, label, Icon]) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className="btn btn-sm"
                style={{
                  background: tab === id ? 'var(--grad-primary)' : 'transparent',
                  color: tab === id ? '#fff' : 'var(--clr-muted)',
                  border: 'none',
                  gap: 6,
                }}
              >
                <Icon size={13} />{label}
              </button>
            ))}
          </div>
          <button className="btn btn-ghost btn-sm" onClick={load} disabled={loading}>
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
          </button>
        </div>

        {/* Users tab */}
        {tab === 'users' && (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            {loading ? (
              <div style={{ padding: 60, display: 'flex', justifyContent: 'center' }}><div className="spinner" /></div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Email</th>
                      <th>Role</th>
                      <th>Status</th>
                      <th>Joined</th>
                      <th style={{ textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map(u => (
                      <tr key={u.id}>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <div style={{
                              width: 30, height: 30, borderRadius: '50%',
                              background: u.role === 'ADMIN' ? 'var(--grad-primary)' : 'var(--clr-surface2)',
                              border: '1px solid var(--clr-border)',
                              display: 'flex', alignItems: 'center', justifyContent: 'center',
                              fontSize: 12, fontWeight: 700,
                            }}>
                              {u.name?.[0]?.toUpperCase()}
                            </div>
                            <span style={{ fontWeight: 500 }}>{u.name}</span>
                          </div>
                        </td>
                        <td style={{ color: 'var(--clr-muted)', fontSize: 12 }}>{u.email}</td>
                        <td><span className={`badge badge-${u.role.toLowerCase()}`}>{u.role}</span></td>
                        <td>
                          <span className={`badge ${u.is_active ? 'badge-online' : 'badge-offline'}`}>
                            {u.is_active ? 'Active' : 'Disabled'}
                          </span>
                        </td>
                        <td style={{ fontSize: 12, color: 'var(--clr-muted)' }}>
                          {new Date(u.created_at).toLocaleDateString()}
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                            {u.role !== 'ADMIN' && (
                              <button
                                className="btn btn-ghost btn-sm"
                                onClick={() => promote(u)}
                                disabled={actionId === u.id}
                                title="Promote to Admin"
                              >
                                <ShieldCheck size={13} />
                              </button>
                            )}
                            <button
                              className="btn btn-ghost btn-sm"
                              onClick={() => toggleUser(u)}
                              disabled={actionId === u.id}
                              style={{ color: u.is_active ? 'var(--clr-danger)' : 'var(--clr-success)' }}
                              title={u.is_active ? 'Disable user' : 'Enable user'}
                            >
                              {u.is_active ? <UserX size={13} /> : <UserCheck size={13} />}
                              {u.is_active ? 'Disable' : 'Enable'}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Audit Logs tab */}
        {tab === 'logs' && (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            {loading ? (
              <div style={{ padding: 60, display: 'flex', justifyContent: 'center' }}><div className="spinner" /></div>
            ) : (
              <div className="table-wrap" style={{ maxHeight: 600, overflowY: 'auto' }}>
                <table>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Action</th>
                      <th>User</th>
                      <th>File</th>
                      <th>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map(log => (
                      <tr key={log.id}>
                        <td style={{ fontSize: 11, color: 'var(--clr-muted)', whiteSpace: 'nowrap' }}>
                          {new Date(log.timestamp).toLocaleString()}
                        </td>
                        <td>
                          <span style={{
                            fontFamily: 'monospace', fontSize: 11, fontWeight: 700,
                            color: actionColors[log.action] || 'var(--clr-muted)',
                          }}>
                            {log.action}
                          </span>
                        </td>
                        <td style={{ fontSize: 12, color: 'var(--clr-muted)' }}>{log.user_email || '—'}</td>
                        <td style={{ fontSize: 12, maxWidth: 200 }} className="truncate">{log.file_name || '—'}</td>
                        <td style={{ fontSize: 12, color: 'var(--clr-muted)', maxWidth: 260 }} className="truncate">
                          {log.details || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
