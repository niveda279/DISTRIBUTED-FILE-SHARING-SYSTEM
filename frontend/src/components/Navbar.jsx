import { Bell, Upload } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Navbar({ onUpload, title, subtitle }) {
  const { user } = useAuth();

  return (
    <header style={{
      height: 'var(--navbar-h)',
      background: 'var(--clr-surface)',
      borderBottom: '1px solid var(--clr-border)',
      display: 'flex',
      alignItems: 'center',
      padding: '0 32px',
      gap: 16,
      flexShrink: 0,
    }}>
      <div style={{ flex: 1 }}>
        <h1 style={{ fontSize: 16, fontWeight: 700, margin: 0, letterSpacing: '-0.2px' }}>{title}</h1>
        {subtitle && <p style={{ fontSize: 12, color: 'var(--clr-muted)', marginTop: 1 }}>{subtitle}</p>}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {onUpload && (
          <button className="btn btn-primary btn-sm" onClick={onUpload}>
            <Upload size={14} />
            Upload
          </button>
        )}
        <div style={{
          width: 32, height: 32, borderRadius: '50%',
          background: 'var(--grad-primary)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 13, fontWeight: 700, color: '#fff',
        }}>
          {user?.name?.[0]?.toUpperCase() || 'U'}
        </div>
      </div>
    </header>
  );
}
