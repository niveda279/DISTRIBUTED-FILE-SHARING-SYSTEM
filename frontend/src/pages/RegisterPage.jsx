import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Database, Eye, EyeOff, UserPlus } from 'lucide-react';
import { authService } from '../services/authService';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

export default function RegisterPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' });
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);

  const handle = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }));

  const submit = async e => {
    e.preventDefault();
    if (form.password !== form.confirm) {
      toast.error('Passwords do not match');
      return;
    }
    if (form.password.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }
    setLoading(true);
    try {
      await authService.register(form.name, form.email, form.password);
      toast.success('Account created! Signing you in…');
      const user = await login(form.email, form.password);
      navigate(user.role === 'ADMIN' ? '/admin' : '/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-hero">
        <div style={{ position: 'relative', zIndex: 1, textAlign: 'center' }}>
          <div style={{
            width: 80, height: 80, borderRadius: 20,
            background: 'var(--grad-accent)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 24px', boxShadow: '0 0 24px rgba(0,229,196,0.3)',
          }}>
            <Database size={40} color="#fff" />
          </div>
          <h2 style={{ fontSize: 32, fontWeight: 900, letterSpacing: '-1px', marginBottom: 16 }}>
            Join DFS System
          </h2>
          <p style={{ color: 'var(--clr-muted)', fontSize: 15, lineHeight: 1.7, maxWidth: 360 }}>
            Get instant access to distributed, fault-tolerant file storage
            with automatic replication.
          </p>
        </div>
      </div>

      <div className="auth-form-section">
        <div className="auth-form-box">
          <div className="auth-logo">
            <div className="auth-logo-icon">
              <Database size={20} color="#fff" />
            </div>
            <span className="auth-logo-name">DFS System</span>
          </div>
          <div className="auth-divider" />
          <h1 className="auth-title">Create account</h1>
          <p className="auth-subtitle">Start sharing files securely today.</p>

          <form onSubmit={submit}>
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input
                id="reg-name"
                className="form-input"
                type="text"
                name="name"
                placeholder="John Doe"
                value={form.name}
                onChange={handle}
                required
                autoFocus
              />
            </div>
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input
                id="reg-email"
                className="form-input"
                type="email"
                name="email"
                placeholder="you@example.com"
                value={form.email}
                onChange={handle}
                required
              />
            </div>
            <div className="form-group" style={{ position: 'relative' }}>
              <label className="form-label">Password</label>
              <input
                id="reg-password"
                className="form-input"
                type={show ? 'text' : 'password'}
                name="password"
                placeholder="Min 8 characters"
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
            <div className="form-group">
              <label className="form-label">Confirm Password</label>
              <input
                id="reg-confirm"
                className="form-input"
                type={show ? 'text' : 'password'}
                name="confirm"
                placeholder="Repeat password"
                value={form.confirm}
                onChange={handle}
                required
              />
            </div>

            <button
              id="reg-submit"
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ width: '100%', justifyContent: 'center', padding: '12px', fontSize: 15 }}
            >
              {loading ? (
                <><span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />Creating…</>
              ) : (
                <><UserPlus size={16} />Create Account</>
              )}
            </button>
          </form>

          <p className="auth-footer">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
