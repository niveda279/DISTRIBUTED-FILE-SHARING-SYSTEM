import { useState, useEffect } from 'react';
import { X, Share2, Trash2, Copy, Check } from 'lucide-react';
import { fileService } from '../services/fileService';
import toast from 'react-hot-toast';

export default function ShareModal({ file, onClose }) {
  const [perms, setPerms] = useState([]);
  const [email, setEmail] = useState('');
  const [perm, setPerm] = useState('VIEW');
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!file) return;
    fileService.listPermissions(file.id)
      .then(setPerms)
      .catch(() => {})
      .finally(() => setFetching(false));
  }, [file]);

  const handleShare = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    try {
      const newPerm = await fileService.shareFile(file.id, email.trim(), perm);
      setPerms(prev => [...prev, newPerm]);
      setEmail('');
      toast.success(`Shared with ${email}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to share');
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (permId) => {
    try {
      await fileService.revokePermission(file.id, permId);
      setPerms(prev => prev.filter(p => p.id !== permId));
      toast.success('Permission revoked');
    } catch {
      toast.error('Failed to revoke');
    }
  };

  const copyLink = () => {
    navigator.clipboard.writeText(`${window.location.origin}/files/${file.id}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!file) return null;

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 8, background: 'rgba(0,229,196,0.12)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--clr-accent)',
            }}>
              <Share2 size={18} />
            </div>
            <div>
              <div className="modal-title">Share File</div>
              <div style={{ fontSize: 12, color: 'var(--clr-muted)' }} className="truncate">
                {file.original_filename}
              </div>
            </div>
          </div>
          <button className="btn-icon btn-ghost" onClick={onClose}><X size={18} /></button>
        </div>

        {/* Add share */}
        <form onSubmit={handleShare}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <input
              className="form-input"
              type="email"
              placeholder="Enter email address…"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              style={{ flex: 1 }}
            />
            <select
              className="form-input"
              value={perm}
              onChange={e => setPerm(e.target.value)}
              style={{ width: 120 }}
            >
              <option value="VIEW">View</option>
              <option value="DOWNLOAD">Download</option>
              <option value="MANAGE">Manage</option>
            </select>
            <button type="submit" className="btn btn-primary" disabled={loading} style={{ whiteSpace: 'nowrap' }}>
              {loading ? '…' : 'Share'}
            </button>
          </div>
        </form>

        {/* Current permissions */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--clr-muted)',
            textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
            Shared With
          </div>
          {fetching ? (
            <div style={{ color: 'var(--clr-muted)', fontSize: 13 }}>Loading…</div>
          ) : perms.length === 0 ? (
            <div style={{ color: 'var(--clr-muted)', fontSize: 13, textAlign: 'center', padding: '16px 0' }}>
              Not shared with anyone yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 200, overflowY: 'auto' }}>
              {perms.map(p => (
                <div key={p.id} style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '10px 12px', borderRadius: 8,
                  background: 'var(--clr-surface2)',
                  border: '1px solid var(--clr-border)',
                }}>
                  <div style={{
                    width: 30, height: 30, borderRadius: '50%',
                    background: 'var(--grad-accent)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 12, fontWeight: 700, color: '#fff', flexShrink: 0,
                  }}>
                    {p.shared_with_name?.[0]?.toUpperCase() || '?'}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{p.shared_with_name}</div>
                    <div style={{ fontSize: 11, color: 'var(--clr-muted)' }}>{p.shared_with_email}</div>
                  </div>
                  <span className={`badge badge-${p.permission.toLowerCase()}`}>{p.permission}</span>
                  <button
                    className="btn-icon btn-ghost btn-sm"
                    onClick={() => handleRevoke(p.id)}
                    title="Revoke access"
                  >
                    <Trash2 size={14} color="var(--clr-danger)" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Copy link */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 14px', borderRadius: 8,
          background: 'var(--clr-surface2)', border: '1px solid var(--clr-border)',
        }}>
          <div style={{ flex: 1, fontSize: 12, color: 'var(--clr-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {window.location.origin}/files/{file.id}
          </div>
          <button className="btn btn-ghost btn-sm" onClick={copyLink}>
            {copied ? <Check size={14} color="var(--clr-success)" /> : <Copy size={14} />}
            {copied ? 'Copied!' : 'Copy Link'}
          </button>
        </div>
      </div>
    </div>
  );
}
