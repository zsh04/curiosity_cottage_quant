
import React from 'react';

const Sidebar = () => {
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
                <ul style={{ listStyle: 'none' }}>
                    {['Dashboard', 'Market Data', 'Agents', 'Settings'].map((item, index) => (
                        <li key={item} style={{ marginBottom: 'var(--space-sm)' }}>
                            <a href="#" style={{
                                display: 'block',
                                padding: 'var(--space-sm) var(--space-md)',
                                borderRadius: 'var(--radius-md)',
                                color: index === 0 ? 'var(--color-primary)' : 'var(--color-text-muted)',
                                background: index === 0 ? 'hsla(var(--h-primary), var(--s-primary), var(--l-primary), 0.1)' : 'transparent',
                                textDecoration: 'none',
                                fontWeight: index === 0 ? 600 : 400,
                                transition: 'all 0.2s'
                            }}>
                                {item}
                            </a>
                        </li>
                    ))}
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
