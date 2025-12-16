
import React from 'react';

const Card = ({ children, className = '', title, actions }) => {
    return (
        <div className={`glass-panel p-6 ${className}`} style={{ padding: 'var(--space-lg)' }}>
            {(title || actions) && (
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: 'var(--space-md)'
                }}>
                    {title && <h3 style={{ margin: 0 }}>{title}</h3>}
                    {actions && <div>{actions}</div>}
                </div>
            )}
            {children}
        </div>
    );
};

export default Card;
