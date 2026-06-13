import { NavLink, Outlet } from 'react-router-dom';

const navItems = [
  { to: '/login', label: 'Login' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/jobs', label: 'Jobs' }
];

export function AppLayout() {
  return (
    <div className="layout">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand-block">
            <span className="brand-mark">A</span>
            <div>
              <div className="brand-title">Arshin Excel Verifier</div>
              <div className="brand-subtitle">Frontend MVP shell</div>
            </div>
          </div>

          <nav className="nav" aria-label="Primary navigation">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  isActive ? 'nav-link nav-link-active' : 'nav-link'
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
