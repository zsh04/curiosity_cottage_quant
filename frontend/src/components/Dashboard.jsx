
import React, { useEffect, useState } from 'react';
import Card from './Card';

const StatWidget = ({ label, value, trend, trendUp }) => (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
        <span style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>{label}</span>
        <div style={{ display: 'flex', alignItems: 'baseline', marginTop: 'var(--space-xs)' }}>
            <span style={{ fontSize: '2rem', fontWeight: 600, color: 'var(--color-text-main)' }}>{value}</span>
            {trend && (
                <span style={{
                    marginLeft: 'var(--space-sm)',
                    fontSize: '0.875rem',
                    color: trendUp ? 'var(--color-success)' : 'var(--color-danger)'
                }}>
                    {trendUp ? '↑' : '↓'} {trend}
                </span>
            )}
        </div>
    </div>
);

const Dashboard = () => {
    const [metrics, setMetrics] = useState(null);
    const [status, setStatus] = useState(null);
    const [signals, setSignals] = useState([]);
    const [loading, setLoading] = useState(true);

    const handleAction = async (action) => {
        try {
            const res = await fetch(`/api/actions/${action}`, { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                alert(`Action Triggered: ${data.message}`);
            } else {
                alert('Action Failed');
            }
        } catch (err) {
            console.error(err);
            alert('Failed to trigger action');
        }
    };

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [metricsRes, statusRes, signalsRes] = await Promise.all([
                    fetch('/api/system/metrics'),
                    fetch('/api/system/status'),
                    fetch('/api/signals')
                ]);

                if (metricsRes.ok && statusRes.ok && signalsRes.ok) {
                    const metricsData = await metricsRes.json();
                    const statusData = await statusRes.json();
                    const signalsData = await signalsRes.json();
                    setMetrics(metricsData);
                    setStatus(statusData);
                    setSignals(signalsData);
                }
            } catch (error) {
                console.error("Failed to fetch dashboard data", error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 5000); // Poll every 5s
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return <div style={{ padding: 'var(--space-xl)', color: 'var(--color-text-muted)' }}>Loading System Data...</div>;
    }

    return (
        <div>
            <header style={{ marginBottom: 'var(--space-xl)' }}>
                <h1 className="animate-fade-in">Control Center</h1>
                <p style={{ color: 'var(--color-text-muted)' }}>
                    System Status: <span style={{ color: status?.status === 'Online' ? 'var(--color-success)' : 'var(--color-danger)' }}>
                        ● {status?.status || 'Unknown'}
                    </span>
                    <span style={{ marginLeft: 'var(--space-md)' }}>v{status?.version}</span>
                </p>
            </header>

            {/* Stats Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                gap: 'var(--space-lg)',
                marginBottom: 'var(--space-xl)'
            }}>
                <Card>
                    <StatWidget
                        label="Total PnL (24h)"
                        value={metrics ? `$${metrics.pnl_24h.toLocaleString()}` : '---'}
                        trend={metrics ? `${metrics.pnl_trend_pct}%` : null}
                        trendUp={metrics?.pnl_trend_pct >= 0}
                    />
                </Card>
                <Card>
                    <StatWidget label="Active Agents" value={status?.active_agents ?? '0'} trend="Stable" trendUp={true} />
                </Card>
                <Card>
                    <StatWidget
                        label="System Load"
                        value={metrics ? `${metrics.system_load_pct}%` : '---'}
                        trend="1.2%"
                        trendUp={false}
                    />
                </Card>
                <Card>
                    <StatWidget label="Open Positions" value={metrics?.open_positions ?? '0'} />
                </Card>
            </div>

            {/* Main Content Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: '2fr 1fr',
                gap: 'var(--space-lg)'
            }}>
                {/* Left Column: Charts/Logs */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
                    <Card title="Live Market Activity">
                        <div style={{
                            height: '300px',
                            background: 'linear-gradient(180deg, var(--color-bg-paper) 0%, transparent 100%)',
                            borderRadius: 'var(--radius-md)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'var(--color-text-muted)'
                        }}>
                            [Market Chart Visualization Placeholder]
                        </div>
                    </Card>

                    <Card title="Recent Signals" className="animate-fade-in" style={{ animationDelay: '0.1s' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                                    <th style={{ padding: 'var(--space-sm)', color: 'var(--color-text-muted)' }}>Time</th>
                                    <th style={{ padding: 'var(--space-sm)', color: 'var(--color-text-muted)' }}>Symbol</th>
                                    <th style={{ padding: 'var(--space-sm)', color: 'var(--color-text-muted)' }}>Action</th>
                                    <th style={{ padding: 'var(--space-sm)', color: 'var(--color-text-muted)' }}>Confidence</th>
                                </tr>
                            </thead>

                            <tbody>
                                {Array.isArray(signals) && signals.map((row, i) => (
                                    <tr key={i} style={{ borderBottom: '1px solid var(--border-color)' }}>
                                        <td style={{ padding: 'var(--space-sm)' }}>{row.time}</td>
                                        <td style={{ padding: 'var(--space-sm)', fontWeight: 600 }}>{row.symbol}</td>
                                        <td style={{ padding: 'var(--space-sm)' }}>
                                            <span style={{
                                                color: row.action === 'LONG' ? 'var(--color-success)' :
                                                    row.action === 'SHORT' ? 'var(--color-danger)' : 'var(--color-text-muted)'
                                            }}>
                                                {row.action}
                                            </span>
                                        </td>
                                        <td style={{ padding: 'var(--space-sm)' }}>{row.confidence}</td>
                                    </tr>
                                ))}
                                {(!signals || signals.length === 0) && (
                                    <tr>
                                        <td colSpan="4" style={{ padding: 'var(--space-md)', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                                            No signals found
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </Card>
                </div>

                {/* Right Column: Controls/Status */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
                    <Card title="Quick Actions">
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                            <button
                                className="btn-primary"
                                onClick={() => handleAction('halt')}
                            >
                                Emergency Halt
                            </button>
                            <button
                                className="btn-primary"
                                style={{ background: 'var(--color-bg-paper)', border: '1px solid var(--border-color)', color: 'var(--color-text-main)' }}
                                onClick={() => handleAction('rebalance')}
                            >
                                Rebalance Portfolio
                            </button>
                            <button
                                className="btn-primary"
                                style={{ background: 'var(--color-bg-paper)', border: '1px solid var(--border-color)', color: 'var(--color-text-main)' }}
                                onClick={() => handleAction('export-logs')}
                            >
                                Export Logs
                            </button>
                        </div>
                    </Card>

                    <Card title="System Health">
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
                            {['Data Feed', 'Execution Engine', 'Risk Manager'].map(service => (
                                <div key={service} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span>{service}</span>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
                                        <span style={{
                                            width: '8px', height: '8px', borderRadius: '50%',
                                            background: 'var(--color-success)',
                                            boxShadow: '0 0 8px var(--color-success)'
                                        }} />
                                        <span style={{ fontSize: '0.875rem', color: 'var(--color-success)' }}>Running</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
