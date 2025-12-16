import React, { useState } from 'react';
import PhysicsGauge from './PhysicsGauge';
import SentimentTriad from './SentimentTriad';
import AgentMonitor from './AgentMonitor';
import ModelMonitor from './ModelMonitor';
import CerebroChart from './CerebroChart';
import AutopsyPanel from './AutopsyPanel';

const Dashboard = () => {
    const [selectedLog, setSelectedLog] = useState(null);

    const handleHalt = () => {
        alert("HALT SIGNAL SENT: Disabling Live Trading...");
        // Actual API call would go here
    };

    // Mock Data for CerebroChart
    const generateChartData = () => {
        const data = [];
        const now = new Date();

        // Generate 20 history points
        for (let i = 20; i > 0; i--) {
            const time = new Date(now.getTime() - i * 60000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            data.push({
                time,
                price: 450 + Math.sin(i * 0.5) * 2 + Math.random(),
                isForecast: false
            });
        }

        // Generate 10 forecast points
        let lastPrice = data[data.length - 1].price || 450;
        for (let i = 0; i < 10; i++) {
            const time = new Date(now.getTime() + i * 60000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const noise = Math.random() * 2;
            data.push({
                time,
                median: lastPrice + i * 0.2 + noise,
                p10: lastPrice + i * 0.1 - (i * 0.5),
                p90: lastPrice + i * 0.3 + (i * 0.6),
                isForecast: true
            });
        }
        return data;
    };

    const chartData = generateChartData();

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-emerald-500/30">

            {/* --- Sticky Header --- */}
            <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
                <div className="container mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_10px_rgba(16,185,129,0.5)]"></div>
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
                                <PhysicsGauge alpha={2.4} />
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
                            <SentimentTriad />
                        </div>

                        {/* Forecast Chart (Cerebro) */}
                        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 shadow-xl flex-[3] relative overflow-hidden flex flex-col">
                            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Chronos Forecast</h2>
                            <div className="flex-1 w-full h-full">
                                <CerebroChart data={chartData} />
                            </div>
                        </div>

                    </section>

                    {/* --- Column 3: System Logs (Span 4) --- */}
                    <section className="lg:col-span-4 h-full">
                        <AgentMonitor onLogClick={setSelectedLog} />
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
