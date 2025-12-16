import React, { useState, useEffect } from 'react';
import PhysicsGauge from './PhysicsGauge';
import SentimentTriad from './SentimentTriad';
import AgentMonitor from './AgentMonitor';
import ModelMonitor from './ModelMonitor';
import CerebroChart from './CerebroChart';
import AutopsyPanel from './AutopsyPanel';

const Dashboard = () => {
    const [selectedLog, setSelectedLog] = useState(null);
    const [isConnected, setIsConnected] = useState(false);

    // System State from Live Backend
    const [systemState, setSystemState] = useState({
        market: {
            alpha: 3.0,
            velocity: 0.0,
            acceleration: 0.0,
            regime: 'Unknown',
            price: 0.0,
            symbol: 'SPY',
            history: []
        },
        signal: {
            side: 'FLAT',
            confidence: 0.0,
            reasoning: 'Initializing...',
            strategy: 'None',
            score: 0.0
        },
        sentiment: {
            label: 'Neutral',
            score: 0.5
        },
        forecast: null,
        logs: []
    });

    // WebSocket Connection
    useEffect(() => {
        const WS_URL = 'ws://localhost:8000/api/ws/stream';
        let ws = null;
        let reconnectTimeout = null;

        const connect = () => {
            ws = new WebSocket(WS_URL);

            ws.onopen = () => {
                console.log('✅ WebSocket Connected');
                setIsConnected(true);
            };

            ws.onmessage = (event) => {
                try {
                    const packet = JSON.parse(event.data);

                    // Update system state with incoming data
                    setSystemState((prevState) => ({
                        market: {
                            ...prevState.market,
                            ...packet.market
                        },
                        signal: {
                            ...prevState.signal,
                            ...packet.signal
                        },
                        sentiment: packet.sentiment || prevState.sentiment,
                        forecast: packet.forecast || prevState.forecast,
                        // Prepend new packet to logs (keep last 50)
                        logs: [packet, ...prevState.logs].slice(0, 50)
                    }));
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            ws.onclose = () => {
                console.log('❌ WebSocket Disconnected');
                setIsConnected(false);

                // Attempt reconnection after 5 seconds
                reconnectTimeout = setTimeout(() => {
                    console.log('🔄 Attempting to reconnect...');
                    connect();
                }, 5000);
            };
        };

        connect();

        // Cleanup on unmount
        return () => {
            if (reconnectTimeout) clearTimeout(reconnectTimeout);
            if (ws) ws.close();
        };
    }, []);

    const handleHalt = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/actions/halt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const result = await response.json();
            alert(result.message || 'HALT SIGNAL SENT');
        } catch (error) {
            alert('Failed to send halt signal: ' + error.message);
        }
    };

    // Generate chart data from history and forecast
    const generateChartData = (history, forecast, currentPrice) => {
        const data = [];
        const now = new Date();

        // Historical data from price history
        if (history && history.length > 0) {
            const recentHistory = history.slice(-20); // Last 20 points
            recentHistory.forEach((price, index) => {
                const time = new Date(now.getTime() - (recentHistory.length - index) * 60000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                data.push({
                    time,
                    price: price,
                    isForecast: false
                });
            });
        }

        // Add current price
        if (currentPrice && currentPrice > 0) {
            data.push({
                time: now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                price: currentPrice,
                isForecast: false
            });
        }

        // Forecast data
        if (forecast && forecast.median && forecast.median.length > 0) {
            forecast.median.forEach((median, index) => {
                const time = new Date(now.getTime() + (index + 1) * 60000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                data.push({
                    time,
                    median: median,
                    p10: forecast.p10?.[index] || median * 0.98,
                    p90: forecast.p90?.[index] || median * 1.02,
                    isForecast: true
                });
            });
        }

        return data.length > 0 ? data : [{ time: 'No Data', price: 0 }];
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-emerald-500/30">

            {/* --- Sticky Header --- */}
            <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
                <div className="container mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        {/* Connection Status Indicator */}
                        <div
                            className={`w-3 h-3 rounded-full shadow-[0_0_10px_rgba(16,185,129,0.5)] ${isConnected
                                ? 'bg-emerald-500 animate-pulse'
                                : 'bg-red-500'
                                }`}
                        ></div>
                        <h1 className="text-lg font-bold tracking-[0.2em] text-slate-100">
                            CURIOSITY COTTAGE <span className="text-emerald-500 text-xs align-top">v2.0</span>
                        </h1>
                    </div>

                    <div className="flex items-center gap-6">
                        <div className="text-xs font-mono text-slate-500 hidden md:block">
                            SYSTEM_MODE: <span className="text-emerald-400">AUTONOMOUS</span>
                        </div>

                        {/* Kill Switch */}
                        <button
                            onClick={handleHalt}
                            className="bg-red-600 hover:bg-red-700 text-white text-xs font-bold py-2 px-4 rounded shadow-[0_0_15px_rgba(220,38,38,0.5)] animate-pulse hover:animate-none transition-all"
                        >
                            EMERGENCY HALT
                        </button>
                    </div>
                </div>
            </header>

            {/* --- Main Mission Control Grid --- */}
            <main className="container mx-auto p-6">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-7rem)]">

                    {/* --- Column 1: Physics & Safety (Span 3) --- */}
                    <section className="lg:col-span-3 flex flex-col gap-6">

                        {/* Physics Gauge Card */}
                        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 shadow-xl backdrop-blur-sm flex-[2] flex flex-col">
                            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Physics Veto</h2>
                            <div className="flex-1 flex items-center justify-center">
                                <PhysicsGauge data={systemState.market} />
                            </div>
                        </div>

                        {/* Model Monitor (Latency) */}
                        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 shadow-xl flex-[3] flex flex-col overflow-hidden">
                            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">System Latency</h2>
                            <div className="flex-1">
                                <ModelMonitor />
                            </div>
                        </div>

                        {/* Legacy Risk Stats (Compact) */}
                        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 shadow-xl flex-1 flex flex-col justify-center">
                            <div className="flex justify-between items-center text-xs font-mono">
                                <span className="text-slate-500 uppercase tracking-wider">Exposure</span>
                                <span className="text-slate-200">$12,450</span>
                            </div>
                        </div>

                    </section>

                    {/* --- Column 2: Cognitive Layer (Span 5) --- */}
                    <section className="lg:col-span-5 flex flex-col gap-6">

                        {/* Sentiment Triad Card */}
                        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 shadow-xl flex-[2] flex flex-col items-center justify-center">
                            <div className="w-full text-left mb-2">
                                <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Market Sentiment</h2>
                            </div>
                            <SentimentTriad
                                label={systemState.sentiment?.label || 'Neutral'}
                                score={systemState.sentiment?.score || 0.5}
                            />
                        </div>

                        {/* Forecast Chart (Cerebro) */}
                        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 shadow-xl flex-[3] relative overflow-hidden flex flex-col">
                            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Chronos Forecast</h2>
                            <div className="flex-1 w-full h-full">
                                <CerebroChart
                                    data={generateChartData(systemState.market.history, systemState.forecast, systemState.market.price)}
                                />
                            </div>
                        </div>

                    </section>

                    {/* --- Column 3: System Logs (Span 4) --- */}
                    <section className="lg:col-span-4 h-full">
                        <AgentMonitor logs={systemState.logs} onLogClick={setSelectedLog} />
                    </section>

                </div>
            </main>

            {/* --- Overlay Modal --- */}
            <AutopsyPanel
                isOpen={!!selectedLog}
                onClose={() => setSelectedLog(null)}
                data={selectedLog}
            />

        </div>
    );
};

export default Dashboard;
