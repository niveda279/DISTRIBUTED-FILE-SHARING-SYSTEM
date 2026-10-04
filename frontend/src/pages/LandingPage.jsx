import { Link } from 'react-router-dom';
import {
  Database, Shield, Zap, Server, ArrowRight, Lock, RefreshCw, CheckCircle,
} from 'lucide-react';

const features = [
  {
    icon: Shield,
    title: 'SHA-256 Integrity',
    desc: 'Every file is verified with cryptographic checksums to prevent tampering or corruption.',
  },
  {
    icon: RefreshCw,
    title: 'Auto Replication',
    desc: 'Files are automatically replicated across storage nodes for redundancy and availability.',
  },
  {
    icon: Zap,
    title: 'Load Balancing',
    desc: 'Intelligent node selection based on real-time availability and storage utilization.',
  },
  {
    icon: Lock,
    title: 'JWT Authentication',
    desc: 'Secure access control with role-based permissions and fine-grained file sharing.',
  },
  {
    icon: Server,
    title: 'Fault Tolerance',
    desc: 'System automatically reroutes to healthy nodes when a storage node goes offline.',
  },
  {
    icon: CheckCircle,
    title: 'Multi-Node Storage',
    desc: 'Three independent storage nodes with real-time health monitoring and heartbeats.',
  },
];

export default function LandingPage() {
  return (
    <div className="landing-page">
      {/* Navbar */}
      <nav className="landing-nav">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 8,
            background: 'var(--grad-primary)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Database size={18} color="#fff" />
          </div>
          <span style={{ fontWeight: 800, fontSize: 16, letterSpacing: '-0.3px' }}>DFS System</span>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <Link to="/login" className="btn btn-ghost btn-sm">Sign In</Link>
          <Link to="/register" className="btn btn-primary btn-sm">Get Started</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="landing-hero">
        <div className="landing-tag">
          <Zap size={12} />
          Fault-tolerant · Distributed · Secure
        </div>
        <h1 className="landing-h1">
          File Sharing<br />
          <span>Reinvented</span>
        </h1>
        <p className="landing-desc">
          A distributed file storage system with automatic replication,
          real-time node health monitoring, and SHA-256 integrity verification.
          Your files, always available.
        </p>
        <div className="landing-actions">
          <Link
            to="/register"
            className="landing-btn-xl"
            style={{ background: 'var(--grad-primary)', color: '#fff', boxShadow: '0 8px 24px rgba(99,120,255,0.4)' }}
          >
            Start Uploading <ArrowRight size={18} />
          </Link>
          <Link
            to="/login"
            className="landing-btn-xl"
            style={{ background: 'var(--clr-surface)', border: '1px solid var(--clr-border)', color: 'var(--clr-text)' }}
          >
            Sign In
          </Link>
        </div>

        {/* Decorative node grid */}
        <div style={{
          display: 'flex', gap: 12, marginTop: 56,
          flexWrap: 'wrap', justifyContent: 'center',
        }}>
          {['Node 1 · Online', 'Node 2 · Online', 'Node 3 · Online'].map((n, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '8px 16px', borderRadius: 100,
              background: 'rgba(35,209,139,0.08)',
              border: '1px solid rgba(35,209,139,0.25)',
              fontSize: 12, fontWeight: 600,
              color: 'var(--clr-success)',
            }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--clr-success)' }} />
              {n}
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="landing-features">
        {features.map(({ icon: Icon, title, desc }) => (
          <div key={title} className="feature-card">
            <div className="feature-icon"><Icon size={22} /></div>
            <div className="feature-title">{title}</div>
            <div className="feature-desc">{desc}</div>
          </div>
        ))}
      </section>

      <footer style={{
        textAlign: 'center', padding: '24px',
        color: 'var(--clr-subtle)', fontSize: 12,
        borderTop: '1px solid var(--clr-border)',
        background: 'var(--clr-bg)',
      }}>
        © 2025 DFS System · Distributed · Encrypted · Always On
      </footer>
    </div>
  );
}
