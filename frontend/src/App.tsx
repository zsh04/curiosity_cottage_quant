import React, { useState, useEffect } from 'react';
import { Terminal, Brain, LayoutDashboard, Loader2 } from 'lucide-react';
import { initTelemetry } from './telemetry';

import DebateConsole from './components/DebateConsole';
import ProTerminal from './components/ProTerminal';
import './index.css';

/**
 * Main Application Layout
 * Provides tabbed switching between different operational views.
 */
function App() {
    const [isReady, setIsReady] = useState(false);
    const [activeTab, setActiveTab] = useState('debate'); // Default to the new Debate Console

    useEffect(() => {
        // Initialize Observability
        initTelemetry();
        setIsReady(true);
    }, []);

    if (!isReady) {
        return (
            <div className="bg-slate-950 min-h-screen flex items-center justify-center text-slate-500 font-mono">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
                    <div className="text-xs tracking-widest">INITIALIZING TELEMETRY...</div>
                </div>
            </div>
        );
    }

    const renderContent = () => {
        switch (activeTab) {
            case 'debate':
                return <DebateConsole />;
            case 'terminal':
                return <ProTerminal />;
            default:
                return <DebateConsole />;
        }
    };

    return (
        <div className="bg-slate-950 min-h-screen flex flex-col font-mono text-slate-200">

            {/* Top Navigation Bar */}
            <nav className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md px-4 h-12 flex items-center justify-between shrink-0 sticky top-0 z-50">

                {/* Brand */}
                <div className="flex items-center gap-2 text-emerald-500 font-bold tracking-wider">
                    <LayoutDashboard className="w-5 h-5" />
                    <span>CURIOSITY COTTAGE // QUANT</span>
                </div>

                {/* Tab Switcher */}
                <div className="flex bg-slate-950 rounded-lg p-1 gap-1 border border-slate-800">
                    <button
                        onClick={() => setActiveTab('debate')}
                        className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-xs font-bold transition-all ${activeTab === 'debate'
                            ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50'
                            : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800'
                            }`}
                    >
                        <Brain className="w-4 h-4" />
                        CONSCIOUSNESS
                    </button>

                    <button
                        onClick={() => setActiveTab('terminal')}
                        className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-xs font-bold transition-all ${activeTab === 'terminal'
                            ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/50'
                            : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800'
                            }`}
                    >
                        <Terminal className="w-4 h-4" />
                        OPERATIONS
                    </button>
                </div>

                {/* System Status Indicators (Mock) */}
                <div className="flex gap-4 text-xs font-mono text-slate-500">
                    <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                        <span>ENGINE: ONLINE</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-blue-500"></div>
                        <span>WS: ACTIVE</span>
                    </div>
                </div>

            </nav>

            {/* Main Content Area */}
            <main className="flex-1 relative overflow-hidden flex flex-col">
                {renderContent()}
            </main>

        </div>
    );
}

export default App;
