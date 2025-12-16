
import { Link, useLocation } from 'react-router-dom';

const Sidebar = () => {
    const location = useLocation();

    const items = [
        { name: 'Dashboard', path: '/' },
        { name: 'Market Data', path: '/market' },
        { name: 'Agents', path: '/agents' },
        { name: 'Settings', path: '/settings' }
    ];

    return (
        <aside style={{
            width: '260px',
            height: '100vh',
            position: 'fixed',
            left: 0,
            top: 0,
            borderRight: '1px solid var(--border-color)',
            padding: 'var(--space-lg)',
            display: 'flex',
            flexDirection: 'column',
            background: 'hsla(var(--h-bg), var(--s-bg), 12%, 0.8)',
            backdropFilter: 'blur(10px)'
        }}>
            <div style={{ marginBottom: 'var(--space-xl)' }}>
                <h2 style={{ fontSize: '1.25rem', color: 'var(--color-primary)' }}>Curiosity<br />Cottage</h2>
            </div>

            <nav style={{ flex: 1 }}>
                <ul style={{ listStyle: 'none', padding: 0 }}>
                    {items.map((item) => {
                        const isActive = location.pathname === item.path;
                        return (
                            <li key={item.name} style={{ marginBottom: 'var(--space-sm)' }}>
                                <Link to={item.path} style={{
                                    display: 'block',
                                    padding: 'var(--space-sm) var(--space-md)',
                                    borderRadius: 'var(--radius-md)',
                                    color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
                                    background: isActive ? 'hsla(var(--h-primary), var(--s-primary), var(--l-primary), 0.1)' : 'transparent',
                                    textDecoration: 'none',
                                    fontWeight: isActive ? 600 : 400,
                                    transition: 'all 0.2s'
                                }}>
                                    {item.name}
                                </Link>
                            </li>
                        );
                    })}
                </ul>
            </nav>

            <div style={{ marginTop: 'auto' }}>
                <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
                    System Status: <span style={{ color: 'var(--color-success)' }}>● Online</span>
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
