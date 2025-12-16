
import React from 'react';
import Sidebar from './Sidebar';

const Layout = ({ children }) => {
    return (
        <div style={{ minHeight: '100vh', display: 'flex' }}>
            <Sidebar />
            <main style={{
                flex: 1,
                marginLeft: '260px',
                padding: 'var(--space-xl)',
                maxWidth: '1600px'
            }}>
                {children}
            </main>
        </div>
    );
};

export default Layout;
