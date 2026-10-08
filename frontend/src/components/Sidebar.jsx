import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Files, Share2, Search, Server, ShieldCheck,
  LogOut, Database, Network, HeartPulse, Zap, Shield, BarChart2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/files',     icon: Files,           label: 'My Files' },
  { to: '/shared',    icon: Share2,           label: 'Shared With Me' },
  { to: '/search',    icon: Search,           label: 'Search' },
  { to: '/nodes',     icon: Server,           label: 'Nodes' },
  { to: '/cluster',   icon: Network,          label: 'Cluster Topology' },
];

const adminItems = [
  { to: '/admin',            icon: ShieldCheck, label: 'Admin Panel' },
  { to: '/admin/healing',    icon: HeartPulse,  label: 'Self-Healing' },
  { to: '/admin/simulation', icon: Zap,         label: 'Chaos Simulation' },
  { to: '/admin/security',   icon: Shield,      label: 'Security Center' },
  { to: '/admin/analytics',  icon: BarChart2,   label: 'Analytics' },
];

export default function Sidebar() {
  const { user, logout } = useAuth();

  return (
    <aside style={{
      width: 'var(--sidebar-w)',
      background: 'var(--clr-surface)',
      borderRight: '1px solid var(--clr-border)',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      overflow: 'hidden',
    }}>
      {/* Logo */}
      <div style={{
        padding: '20px 20px 16px',
        borderBottom: '1px solid var(--clr-border)',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
      }}>
        <div style={{
          width: 36, height: 36, borderRadius: 8,
          background: 'var(--grad-primary)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <Database size={18} color="#fff" />
        </div>
        <div>
          <div style={{ fontWeight: 800, fontSize: 14, letterSpacing: '-0.3px' }}>DFS System</div>
          <div style={{ fontSize: 11, color: 'var(--clr-muted)' }}>Distributed Files</div>
        </div>
      </div>

      {/* Nav items */}
      <nav style={{ flex: 1, padding: '12px 8px', overflowY: 'auto' }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--clr-subtle)',
          padding: '8px 12px 6px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          Main
        </div>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} style={({ isActive }) => ({
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '9px 12px', borderRadius: 8, marginBottom: 2,
            fontWeight: 500, fontSize: 13,
            color: isActive ? '#fff' : 'var(--clr-muted)',
            background: isActive ? 'var(--grad-primary)' : 'transparent',
            transition: 'all 0.15s',
            textDecoration: 'none',
          })}
          onMouseEnter={e => { if (!e.currentTarget.className.includes('active')) e.currentTarget.style.background = 'var(--clr-surface2)'; }}
          onMouseLeave={e => { if (!e.currentTarget.querySelector('[aria-current]')) e.currentTarget.style.background = ''; }}
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}

        {user?.role === 'ADMIN' && (
          <>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--clr-subtle)',
              padding: '16px 12px 6px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Admin
            </div>
            {adminItems.map(({ to, icon: Icon, label }) => (
              <NavLink key={to} to={to} style={({ isActive }) => ({
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '9px 12px', borderRadius: 8, marginBottom: 2,
                fontWeight: 500, fontSize: 13,
                color: isActive ? '#fff' : 'var(--clr-muted)',
                background: isActive ? 'var(--grad-primary)' : 'transparent',
                transition: 'all 0.15s',
                textDecoration: 'none',
              })}>
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </>
        )}
      </nav>

      {/* User profile */}
      <div style={{
        padding: '12px 8px',
        borderTop: '1px solid var(--clr-border)',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 12px', borderRadius: 8,
          background: 'var(--clr-surface2)',
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: '50%',
            background: 'var(--grad-primary)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 13, fontWeight: 700, color: '#fff', flexShrink: 0,
          }}>
            {user?.name?.[0]?.toUpperCase() || 'U'}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {user?.name}
            </div>
            <div style={{ fontSize: 11, color: 'var(--clr-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {user?.role}
            </div>
          </div>
          <button
            onClick={logout}
            title="Logout"
            style={{
              background: 'none', border: 'none', color: 'var(--clr-muted)',
              cursor: 'pointer', padding: 4, borderRadius: 6, flexShrink: 0,
              transition: 'color 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--clr-danger)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--clr-muted)'}
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </aside>
  );
}
