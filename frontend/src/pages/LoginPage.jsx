import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Database, Eye, EyeOff, LogIn } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState({ email: '', password: '' });
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);

  const handle = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }));

  const submit = async e => {
    e.preventDefault();
    setLoading(true);
    try {
      const user = await login(form.email, form.password);
      toast.success(`Welcome back, ${user.name}!`);
      navigate(user.role === 'ADMIN' ? '/admin' : '/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      {/* Hero side */}
      <div className="auth-hero">
        <div style={{ position: 'relative', zIndex: 1, textAlign: 'center' }}>
          <div style={{
            width: 80, height: 80, borderRadius: 20,
            background: 'var(--grad-primary)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 24px', boxShadow: 'var(--shadow-glow)',
          }}>
            <Database size={40} color="#fff" />
          </div>
          <h2 style={{ fontSize: 32, fontWeight: 900, letterSpacing: '-1px', marginBottom: 16 }}>
            Distributed File System
          </h2>
          <p style={{ color: 'var(--clr-muted)', fontSize: 15, lineHeight: 1.7, maxWidth: 360 }}>
            Secure, fault-tolerant file storage with automatic replication
            across multiple storage nodes.
          </p>
          <div style={{ marginTop: 40, display: 'flex', flexDirection: 'column', gap: 12, textAlign: 'left' }}>
            {[
              'SHA-256 integrity verification',
              'Automatic file replication',
              'Real-time node health monitoring',
              'Role-based access control',
            ].map(item => (
              <div key={item} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 14, color: 'var(--clr-muted)' }}>
                <div style={{
                  width: 20, height: 20, borderRadius: '50%',
                  background: 'rgba(99,120,255,0.2)', color: 'var(--clr-primary)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, fontWeight: 700, flexShrink: 0,
                }}>✓</div>
                {item}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Form side */}
      <div className="auth-form-section">
        <div className="auth-form-box">
          <div className="auth-logo">
            <div className="auth-logo-icon">
              <Database size={20} color="#fff" />
            </div>
            <span className="auth-logo-name">DFS System</span>
          </div>
          <div className="auth-divider" />
          <h1 className="auth-title">Welcome back</h1>
          <p className="auth-subtitle">Sign in to your account to continue.</p>

          <form onSubmit={submit}>
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input
                id="login-email"
                className="form-input"
                type="email"
                name="email"
                placeholder="you@example.com"
                value={form.email}
                onChange={handle}
                required
                autoFocus
              />
            </div>
            <div className="form-group" style={{ position: 'relative' }}>
              <label className="form-label">Password</label>
              <input
                id="login-password"
                className="form-input"
                type={show ? 'text' : 'password'}
                name="password"
                placeholder="••••••••"
                value={form.password}
                onChange={handle}
                required
                style={{ paddingRight: 44 }}
              />
              <button
                type="button"
                onClick={() => setShow(s => !s)}
                style={{
                  position: 'absolute', right: 12, bottom: 11,
                  background: 'none', border: 'none', color: 'var(--clr-muted)', cursor: 'pointer',
                }}
              >
                {show ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            <button
              id="login-submit"
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ width: '100%', justifyContent: 'center', padding: '12px', fontSize: 15 }}
            >
              {loading ? (
                <><span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />Signing in…</>
              ) : (
                <><LogIn size={16} />Sign In</>
              )}
            </button>
          </form>

          <p className="auth-footer">
            Don't have an account? <Link to="/register">Create one</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
