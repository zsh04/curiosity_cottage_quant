import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Activity, Lock, Unlock, Shield, AlertTriangle, TrendingUp, TrendingDown, Minus } from 'lucide-react';

/**
 * The Debate Console
 * A real-time visualization of the AI's consciousness stream and decision making tournament.
 */
const DebateConsole = () => {
    // State
    const [logs, setLogs] = useState([]);
    const [activeAnalysts, setActiveAnalysts] = useState({}); // { SYMBOL: { sentiment, velocity, updateTime } }
    const [verdict, setVerdict] = useState(null); // { status: "HOLD", confidence: 0.0, locked: false }
    const [isFrozen, setIsFrozen] = useState(false);
    const [isConnected, setIsConnected] = useState(false);

    const wsRef = useRef(null);
    const scrollRef = useRef(null);

    // Auto-scroll log
    useEffect(() => {
        if (!isFrozen && scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs, isFrozen]);

    // WebSocket Connection
    useEffect(() => {
        const connect = () => {
            // Use correct port and path based on environment
            // Assuming Vite proxy forwards /api to localhost:8000 or similar
            // But direct localhost:8000/api/ws/brain was verified
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = 'localhost:8000'; // Hardcoded for local dev as per verify script
            const url = `${protocol}//${host}/api/ws/brain`;

            console.log('Connecting to Brain:', url);
            const ws = new WebSocket(url);
            wsRef.current = ws;

            ws.onopen = () => {
                setIsConnected(true);
                addLog('SYSTEM', 'Neural Link Established.', 'system');
            };

            ws.onclose = () => {
                setIsConnected(false);
                addLog('SYSTEM', 'Neural Link Severed. Retrying...', 'error');
                setTimeout(connect, 3000);
            };

            ws.onmessage = (event) => {
                if (isFrozen) return;
                try {
                    const data = JSON.parse(event.data);
                    handleBrainEvent(data);
                } catch (e) {
                    console.error("Parse error", e);
                }
            };
        };

        connect();

        return () => {
            if (wsRef.current) wsRef.current.close();
        };
    }, [isFrozen]);

    // Event Handler
    const handleBrainEvent = (data) => {
        const { type, node, symbol, payload } = data;
        const timestamp = new Date().toLocaleTimeString();

        // 1. Log everything to the Arena
        let message = "";
        let level = "info";

        if (type === "NODE_UPDATE") {
            if (node === "macro") {
                message = `Found ${payload.candidates?.length || 0} candidates. Top: ${payload.winner || 'None'}`;
                updateAnalyst(symbol || "SCANNER", { status: "SCANNING", score: 0 });
            } else if (node === "analyst") {
                message = `Analyzed ${symbol}. Signal: ${payload.signal_side} (${(payload.signal_confidence * 100).toFixed(0)}%)`;
                updateAnalyst(symbol, {
                    sentiment: payload.signal_side,
                    score: payload.signal_confidence,
                    velocity: payload.velocity,
                    regime: payload.regime
                });
            }
        } else if (type === "TOURNAMENT_VERDICT") {
            message = `VERDICT: ${payload.rationale}`;
            level = "risk";

            // Update Verdict Panel
            setVerdict({
                status: payload.approved_size > 0 ? "BUY" : "HOLD",
                confidence: payload.signal_confidence || 0,
                locked: payload.approved_size === 0,
                symbol: payload.symbol
            });
        }

        if (message) {
            addLog(node.toUpperCase(), message, level, symbol);
        }
    };

    const updateAnalyst = (symbol, data) => {
        setActiveAnalysts(prev => ({
            ...prev,
            [symbol]: { ...prev[symbol], ...data, lastUpdate: Date.now() }
        }));
    };

    const addLog = (source, text, level = 'info', symbol = null) => {
        setLogs(prev => [...prev.slice(-100), { // Keep last 100
            id: Date.now() + Math.random(),
            time: new Date().toLocaleTimeString(),
            source,
            text,
            level,
            symbol
        }]);
    };

    // Render Helpers
    const getSentimentColor = (side) => {
        if (side === 'BUY') return 'text-emerald-400';
        if (side === 'SELL') return 'text-rose-400';
        return 'text-slate-400';
    };

    const getLogStyle = (level) => {
        if (level === 'risk') return 'text-amber-400 border-l-2 border-amber-500 pl-2';
        if (level === 'error') return 'text-red-500';
        if (level === 'system') return 'text-blue-400 italic';
        return 'text-slate-300';
    };

    return (
        <div className="flex h-screen w-full bg-slate-950 text-slate-200 font-mono overflow-hidden">

            {/* LEFT PANEL: THE ANALYSTS */}
            <div className="w-1/4 border-r border-slate-800 p-4 flex flex-col gap-4 bg-slate-900/50">
                <div className="flex items-center gap-2 text-emerald-500 mb-2">
                    <Activity className="w-5 h-5" />
                    <h2 className="font-bold tracking-wider">ACTIVE ANALYSTS</h2>
                </div>

                <div className="flex-1 overflow-y-auto space-y-3 pr-2">
                    {Object.entries(activeAnalysts).map(([sym, data]) => (
                        <div key={sym} className="p-3 bg-slate-900 border border-slate-800 rounded-lg shadow-lg relative overflow-hidden group hover:border-emerald-500/50 transition-all">
                            {/* Pulse Effect */}
                            <div className={`absolute top-0 right-0 w-2 h-2 rounded-full m-2 ${Date.now() - data.lastUpdate < 2000 ? 'bg-emerald-500 animate-ping' : 'bg-slate-700'}`} />

                            <div className="flex justify-between items-center mb-2">
                                <span className="font-bold text-lg text-white">{sym}</span>
                                <span className={`text-xs font-bold ${getSentimentColor(data.sentiment)}`}>
                                    {data.sentiment || 'ANALYZING'}
                                </span>
                            </div>

                            <div className="grid grid-cols-2 gap-2 text-xs text-slate-500">
                                <div>
                                    <div className="uppercase text-[10px]">Conf</div>
                                    <div className="text-slate-300">{((data.score || 0) * 100).toFixed(0)}%</div>
                                </div>
                                <div>
                                    <div className="uppercase text-[10px]">Regime</div>
                                    <div className="text-slate-300 truncate">{data.regime || '---'}</div>
                                </div>
                            </div>

                            {/* Velocity Arrow */}
                            {data.velocity !== undefined && (
                                <div className="mt-2 flex items-center gap-1 text-xs">
                                    <div className="uppercase text-[10px] w-12">Velocity</div>
                                    {data.velocity > 0 ? <TrendingUp className="w-3 h-3 text-emerald-500" /> : <TrendingDown className="w-3 h-3 text-rose-500" />}
                                    <span className={data.velocity > 0 ? 'text-emerald-500' : 'text-rose-500'}>
                                        {data.velocity.toFixed(4)}
                                    </span>
                                </div>
                            )}
                        </div>
                    ))}
                    {Object.keys(activeAnalysts).length === 0 && (
                        <div className="text-slate-600 text-center italic mt-10">Waiting for market scan...</div>
                    )}
                </div>
            </div>

            {/* CENTER PANEL: THE ARENA (Use flex-1 to take remaining space) */}
            <div className="flex-1 flex flex-col min-w-0 bg-slate-950 px-6 py-4 relative">
                {/* Header */}
                <div className="flex justify-between items-center mb-4 border-b border-slate-800 pb-2">
                    <div className="flex items-center gap-2 text-blue-400">
                        <Terminal className="w-5 h-5" />
                        <h2 className="font-bold tracking-wider">CONSCIOUSNESS STREAM</h2>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold ${isConnected ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'}`}>
                            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                            {isConnected ? 'LIVE' : 'OFFLINE'}
                        </div>
                        <button
                            onClick={() => setIsFrozen(!isFrozen)}
                            className={`px-3 py-1 rounded border text-xs font-bold transition-colors ${isFrozen ? 'bg-blue-600 border-blue-500 text-white' : 'border-slate-700 text-slate-400 hover:text-white hover:border-slate-500'}`}
                        >
                            {isFrozen ? 'RÈSUME' : 'FREEZE'}
                        </button>
                    </div>
                </div>

                {/* Logs Area */}
                <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 font-mono text-sm pb-4">
                    {logs.map((log) => (
                        <div key={log.id} className={`flex gap-3 items-start opacity-90 hover:opacity-100 transition-opacity ${getLogStyle(log.level)}`}>
                            <span className="text-slate-600 whitespace-nowrap text-xs mt-0.5">[{log.time}]</span>
                            <span className="font-bold text-slate-500 whitespace-nowrap text-xs mt-0.5 w-20 text-right">{log.source}:</span>
                            <span className="break-all">{log.text}</span>
                        </div>
                    ))}
                    {logs.length === 0 && (
                        <div className="text-slate-700 text-center mt-20">Initializing neural link... awaiting thoughts.</div>
                    )}
                </div>

                {/* Input Faux-Prompt */}
                <div className="mt-2 text-slate-600 flex items-center gap-2 text-sm border-t border-slate-800 pt-3">
                    <span className="text-emerald-500 animate-pulse">{'>'}</span>
                    <span>Awaiting Logic Synthesis...</span>
                </div>
            </div>

            {/* RIGHT PANEL: THE VERDICT */}
            <div className="w-80 border-l border-slate-800 bg-slate-900/50 flex flex-col">
                <div className="p-6 border-b border-slate-800 bg-slate-900">
                    <div className="text-slate-500 text-xs font-bold uppercase tracking-widest mb-2">Current Verdict</div>

                    <div className="flex flex-col items-center justify-center py-6">
                        {verdict?.status === 'BUY' ? (
                            <div className="w-24 h-24 rounded-full border-4 border-emerald-500 flex items-center justify-center bg-emerald-500/10 shadow-[0_0_20px_rgba(16,185,129,0.3)] animate-pulse">
                                <span className="text-2xl font-black text-emerald-400">BUY</span>
                            </div>
                        ) : verdict?.status === 'SHORT' ? (
                            <div className="w-24 h-24 rounded-full border-4 border-rose-500 flex items-center justify-center bg-rose-500/10 shadow-[0_0_20px_rgba(244,63,94,0.3)] animate-pulse">
                                <span className="text-2xl font-black text-rose-400">SHORT</span>
                            </div>
                        ) : (
                            <div className="w-24 h-24 rounded-full border-4 border-slate-600 flex items-center justify-center bg-slate-800/50">
                                <span className="text-2xl font-black text-slate-500">HOLD</span>
                            </div>
                        )}

                        <div className="mt-4 text-center">
                            <div className="text-white font-bold text-lg">{verdict?.symbol || '---'}</div>
                            <div className="text-slate-500 text-xs">Target Asset</div>
                        </div>
                    </div>
                </div>

                <div className="p-6 flex-1 flex flex-col gap-8">
                    {/* Confidence Meter */}
                    <div>
                        <div className="flex justify-between text-xs font-bold mb-2">
                            <span className="text-slate-400">CONFIDENCE</span>
                            <span className="text-emerald-400">{((verdict?.confidence || 0) * 100).toFixed(0)}%</span>
                        </div>
                        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-emerald-500 transition-all duration-500 ease-out"
                                style={{ width: `${(verdict?.confidence || 0) * 100}%` }}
                            />
                        </div>
                    </div>

                    {/* Physics Lock */}
                    <div className={`p-4 rounded-xl border flex items-center gap-4 transition-colors ${verdict?.locked ? 'bg-slate-900 border-slate-700' : 'bg-emerald-900/20 border-emerald-500/30'}`}>
                        <div className={`p-3 rounded-full ${verdict?.locked ? 'bg-slate-800 text-slate-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                            {verdict?.locked ? <Lock size={24} /> : <Unlock size={24} />}
                        </div>
                        <div>
                            <div className="text-sm font-bold text-slate-200">
                                {verdict?.locked ? 'Safety Locked' : 'Gate Open'}
                            </div>
                            <div className="text-xs text-slate-500">
                                {verdict?.locked ? 'Risk Veto Active' : 'Physics Approved'}
                            </div>
                        </div>
                    </div>

                    {/* Info Box */}
                    <div className="mt-auto p-4 bg-slate-800/50 rounded-lg border border-slate-700 text-xs text-slate-400">
                        <div className="flex items-center gap-2 mb-2 text-slate-300">
                            <Shield size={14} />
                            <span className="font-bold">SYSTEM STATUS</span>
                        </div>
                        <div className="space-y-1">
                            <div className="flex justify-between">
                                <span>Connection</span>
                                <span className={isConnected ? "text-emerald-400" : "text-rose-400"}>{isConnected ? "Secure" : "Lost"}</span>
                            </div>
                            <div className="flex justify-between">
                                <span>Latency</span>
                                <span>~12ms</span>
                            </div>
                            <div className="flex justify-between">
                                <span>Protocol</span>
                                <span>WSS/JSON</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DebateConsole;
