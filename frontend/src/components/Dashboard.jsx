import React from 'react';
import PhysicsGauge from './PhysicsGauge';
import SentimentTriad from './SentimentTriad';
import AgentMonitor from './AgentMonitor';

const Dashboard = () => {
    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-emerald-500/30">

            {/* --- Sticky Header --- */}
            <header className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
                <div className="container mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_10px_rgba(16,185,129,0.5)]"></div>
                        <h1 className="text-lg font-bold tracking-[0.2em] text-slate-100">
                            CURIOSITY COTTAGE <span className="text-emerald-500 text-xs align-top">v2.0</span>
                        </h1>
                    </div>
                    <div className="text-xs font-mono text-slate-500">
                        SYSTEM_MODE: <span className="text-emerald-400">AUTONOMOUS</span>
                    </div>
                </div>
            </header>

            {/* --- Main Mission Control Grid --- */}
            <main className="container mx-auto p-6">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-7rem)]">

                    {/* --- Column 1: Physics & Safety (Span 3) --- */}
                    <section className="lg:col-span-3 flex flex-col gap-6">

                        {/* Physics Gauge Card */}
                        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 shadow-xl backdrop-blur-sm flex-1 flex flex-col">
                            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Physics Veto</h2>
                            <div className="flex-1 flex items-center justify-center">
                                <PhysicsGauge alpha={2.4} />
                            </div>
                        </div>

                        {/* Risk Stats Card */}
                        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 shadow-xl h-1/3">
                            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Risk Telemetry</h2>
                            <div className="space-y-4 font-mono text-sm">
                                <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                                    <span className="text-slate-500">Exposure</span>
                                    <span className="text-slate-200">$12,450</span>
                                </div>
                                <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                                    <span className="text-slate-500">Daily Drawdown</span>
                                    <span className="text-emerald-400">-0.45%</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-slate-500">Kelly Frac</span>
                                    <span className="text-yellow-400">0.32</span>
                                </div>
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

                        {/* Forecast Placeholder Card */}
                        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 shadow-xl flex-1 relative overflow-hidden group">
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-slate-800/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000"></div>
                            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Chronos Forecast</h2>
                            <div className="h-full flex items-center justify-center text-slate-600 font-mono text-xs">
                                [ WAITING FOR PROBABILISTIC INFERENCE ]
                            </div>
                        </div>

                    </section>

                    {/* --- Column 3: System Logs (Span 4) --- */}
                    <section className="lg:col-span-4 h-full">
                        <AgentMonitor />
                    </section>

                </div>
            </main>
        </div>
    );
};

export default Dashboard;
