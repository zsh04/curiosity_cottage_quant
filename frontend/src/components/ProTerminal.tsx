import React, { useState, useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, CandlestickData, ColorType } from 'lightweight-charts';
import { Activity, Zap, Shield, Globe, Terminal, Cpu } from 'lucide-react';

interface Position {
    symbol: string;
    qty: number;
    avg_entry_price: number;
    current_price: number;
    unrealized_pl: number;
    market_value: number;
}

interface ScannerCandidate {
    symbol: string;
    price: number;
    hurst: number;
    signal_potential: number;
    volatility: number;
}

interface TelemetryPacket {
    market?: {
        symbol?: string;
        price?: number;
        alpha?: number;
        velocity?: number;
        history?: any[];
    };
    scanner?: ScannerCandidate[];
    signal?: {
        side?: string;
        confidence?: number;
        reasoning?: string;
        strategy?: string;
    };
}

const ProTerminal: React.FC = () => {
    // --- STATE ---
    const [isConnected, setIsConnected] = useState<boolean>(false);
    const [systemMode, setSystemMode] = useState<string>('PAPER');
    const [positions, setPositions] = useState<Position[]>([]);
    const [telemetry, setTelemetry] = useState<TelemetryPacket | null>(null);
    const [logs, setLogs] = useState<string[]>([]);

    // Order Entry
    const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy');
    const [orderQty, setOrderQty] = useState<string>('');
    const [orderLimit, setOrderLimit] = useState<string>('');

    // Refs
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const logsEndRef = useRef<HTMLDivElement>(null);

    // --- INITIAL DATA LOAD (REST) ---
    useEffect(() => {
        const loadInitialData = async () => {
            try {
                // 1. Fetch History for Chart (Instant Load)
                const histRes = await fetch('http://localhost:8000/api/market/history/SPY?limit=100');
                const histData = await histRes.json();

                if (candleSeriesRef.current && Array.isArray(histData) && histData.length > 0) {
                    // Sort chronologically just in case
                    const sortedData = histData.sort((a: any, b: any) => new Date(a.time).getTime() - new Date(b.time).getTime());
                    candleSeriesRef.current.setData(sortedData);

                    // Initialize Price from last bar
                    const lastBar = sortedData[sortedData.length - 1];
                    setTelemetry(prev => ({
                        ...prev,
                        market: {
                            ...prev?.market,
                            price: lastBar.close,
                            history: histData
                        }
                    }));
                    console.log("✅ Chart Hydrated from REST API");
                }

                // 2. Fetch Initial Positions
                fetchPositions();
            } catch (e) {
                console.error("Initial Load Failed:", e);
                addLog(`Error loading initial data: ${e}`);
            }
        };

        // Initialize Chart first
        if (!chartRef.current && chartContainerRef.current) {
            initChart();
            // Small delay to ensure chart is ready before data
            setTimeout(loadInitialData, 100);
        }
    }, []);

    // --- CHART SETUP ---
    const initChart = () => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#94a3b8',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
            },
            width: chartContainerRef.current.clientWidth,
            height: chartContainerRef.current.clientHeight,
            crosshair: {
                mode: 1, // CrosshairMode.Normal
                vertLine: {
                    width: 1,
                    color: 'rgba(255, 255, 255, 0.4)',
                    style: 3, // LineStyle.Dashed
                    labelBackgroundColor: '#88C0D0',
                },
                horzLine: {
                    width: 1,
                    color: 'rgba(255, 255, 255, 0.4)',
                    style: 3, // LineStyle.Dashed
                    labelBackgroundColor: '#88C0D0',
                },
            },
            rightPriceScale: {
                borderColor: '#2B3339',
            },
            timeScale: {
                borderColor: '#2B3339',
                timeVisible: true,
                secondsVisible: false,
            },
        });

        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#26a69a', // TradingView Green
            downColor: '#ef5350', // TradingView Red
            borderDownColor: '#ef5350',
            borderUpColor: '#26a69a',
            wickDownColor: '#ef5350',
            wickUpColor: '#26a69a',
        });

        chartRef.current = chart;
        candleSeriesRef.current = candlestickSeries;

        // Resize Observer
        const resizeObserver = new ResizeObserver(entries => {
            if (entries.length === 0 || entries[0].target !== chartContainerRef.current) { return; }
            const newRect = entries[0].contentRect;
            chart.applyOptions({ width: newRect.width, height: newRect.height });
        });
        resizeObserver.observe(chartContainerRef.current);
    };

    // --- WEBSOCKET STREAM ---
    useEffect(() => {
        const WS_URL = 'ws://localhost:8000/api/ws/stream';
        let ws: WebSocket;

        const connect = () => {
            ws = new WebSocket(WS_URL);
            ws.onopen = () => {
                setIsConnected(true);
                addLog("System Connected to Nucleus.");
            };
            ws.onmessage = (event) => {
                try {
                    const packet: TelemetryPacket = JSON.parse(event.data);
                    setTelemetry(packet);

                    // Log Reasoning/Debate
                    if (packet.signal && packet.signal.reasoning) {
                        addLog(`[ANALYST] ${packet.signal.reasoning}`);
                    }

                    // Real-time Chart Update
                    if (packet.market && packet.market.history && candleSeriesRef.current) {
                        const bars = packet.market.history;
                        if (bars.length > 0) {
                            const latest = bars[bars.length - 1];
                            // Update current candle
                            candleSeriesRef.current.update({
                                time: latest.timestamp ? latest.timestamp.split('T')[0] : '2024-01-01',
                                open: latest.open,
                                high: latest.high,
                                low: latest.low,
                                close: latest.close
                            } as CandlestickData);
                        }
                    }
                } catch (e) { console.error(e); }
            };
            ws.onclose = () => {
                setIsConnected(false);
                addLog("Connection Lost. Retrying...");
                setTimeout(connect, 3000);
            };
        };

        connect();
        return () => ws?.close();
    }, []);

    // --- ACTIONS ---
    const fetchPositions = async () => {
        try {
            const res = await fetch('http://localhost:8000/api/orders/positions');
            const data = await res.json();
            setPositions(data);
        } catch (e) { console.error(e); }
    };

    const handleOrder = async () => {
        if (!orderQty) return;
        addLog(`Transmitting Order: ${orderSide.toUpperCase()} ${orderQty} SPY...`);
        try {
            const res = await fetch('http://localhost:8000/api/orders/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: 'SPY',
                    qty: parseFloat(orderQty),
                    side: orderSide,
                    type: orderLimit ? 'limit' : 'market',
                    limit_price: orderLimit ? parseFloat(orderLimit) : null
                })
            });
            const data = await res.json();
            if (data.success) {
                addLog(`Execution Confirmed: ${data.message}`);
                fetchPositions();
                setOrderQty('');
            } else {
                addLog(`Order Rejected: ${data.message}`);
            }
        } catch (e: any) {
            addLog(`Transmission Error: ${e.message}`);
        }
    };

    const handleHalt = async () => {
        if (confirm("⚠ ACTIVATE EMERGENCY HALT?")) {
            await fetch('http://localhost:8000/api/actions/halt', { method: 'POST' });
            addLog("!! EMERGENCY HALT TRIGGERED !!");
        }
    };

    const addLog = (msg: string) => {
        setLogs(prev => [...prev.slice(-19), `[${new Date().toLocaleTimeString()}] ${msg}`]);
    };

    // Auto-scroll logs
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [logs]);

    // Derived State
    const scanner = telemetry?.scanner || [];
    const price = telemetry?.market?.price || 0.00;
    const alpha = telemetry?.market?.alpha || 0.00;
    const velocity = telemetry?.market?.velocity || 0.00;
    const signal = telemetry?.signal?.side || 'FLAT';

    return (
        <div className="flex flex-col h-screen p-4 gap-4 font-mono text-sm">
            {/* --- HEADER --- */}
            <header className="glass-panel p-4 rounded-xl flex justify-between items-center z-10">
                <div className="flex items-center gap-3">
                    <Globe className={`w-5 h-5 ${isConnected ? 'text-green-400' : 'text-red-500 animate-pulse'}`} />
                    <h1 className="text-xl font-bold tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500 neon-text-blue">
                        CURIOSITY<span className="text-white font-light opacity-50"> // QUANT</span>
                    </h1>
                </div>

                <div className="flex items-center gap-6">
                    <div className="flex gap-4 text-xs opacity-70">
                        <div className="flex items-center gap-1"><Cpu size={14} /> PING: {isConnected ? '12ms' : '--'}</div>
                        <div className="flex items-center gap-1"><Zap size={14} /> MODE: {systemMode}</div>
                    </div>

                    <button
                        onClick={handleHalt}
                        className="bg-red-500/10 border border-red-500/50 text-red-500 hover:bg-red-500 hover:text-white px-4 py-2 rounded-lg transition-all font-bold tracking-widest text-xs flex items-center gap-2"
                    >
                        <Shield size={14} /> KILL SWITCH
                    </button>
                </div>
            </header>

            {/* --- MAIN DASHBOARD --- */}
            <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">

                {/* LEFT COL: MARKET DATA */}
                <div className="col-span-3 flex flex-col gap-4">
                    {/* PRICE CARD */}
                    <div className="glass-panel p-6 rounded-xl relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                            <Activity size={100} />
                        </div>
                        <h2 className="text-gray-400 text-xs tracking-wider mb-1">ASSET PRICE</h2>
                        <div className="text-4xl font-black text-white">$ {price.toFixed(2)}</div>
                        <div className="flex gap-2 mt-4 text-xs">
                            <div className="bg-white/5 px-2 py-1 rounded">{telemetry?.market?.symbol || 'SPY'}</div>
                            <div className="bg-green-500/20 text-green-400 px-2 py-1 rounded">+0.42%</div>
                        </div>
                    </div>

                    {/* ALPHA GAUGE */}
                    <div className="glass-panel p-6 rounded-xl flex-1 flex flex-col">
                        <h2 className="text-gray-400 text-xs tracking-wider mb-4 flex items-center gap-2">
                            <Zap size={14} className="text-yellow-400" /> ALPHA PHYSICS
                        </h2>

                        <div className="space-y-4">
                            <div>
                                <div className="flex justify-between mb-1">
                                    <span className="text-xs">Tail Alpha</span>
                                    <span className="text-xs font-bold text-cyan-400">{alpha.toFixed(2)}</span>
                                </div>
                                <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.5)] transition-all duration-500"
                                        style={{ width: `${Math.min(alpha * 20, 100)}%` }}
                                    />
                                </div>
                            </div>

                            <div>
                                <div className="flex justify-between mb-1">
                                    <span className="text-xs">Velocity</span>
                                    <span className="text-xs font-bold text-pink-400">{velocity.toFixed(4)}</span>
                                </div>
                                <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-pink-400 shadow-[0_0_10px_rgba(244,114,182,0.5)] transition-all duration-500"
                                        style={{ width: `${Math.min(Math.abs(velocity) * 500, 100)}%` }}
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="mt-auto py-4">
                            <div className="glass-input p-3 rounded-lg text-center">
                                <div className="text-[10px] text-gray-500 uppercase">Current Signal</div>
                                <div className={`text-xl font-bold tracking-widest ${signal === 'buy' ? 'text-green-400' : signal === 'sell' ? 'text-red-400' : 'text-gray-400'}`}>
                                    {signal.toUpperCase()}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* MIDDLE COL: CHART */}
                <div className="col-span-6 glass-panel rounded-xl p-4 flex flex-col relative">
                    <div className="absolute top-4 left-4 z-10 flex gap-2">
                        <div className="glass-input px-3 py-1 rounded text-xs font-mono">1D</div>
                        <div className="glass-input px-3 py-1 rounded text-xs font-mono opacity-50 hover:opacity-100 cursor-pointer">1H</div>
                    </div>
                    <div ref={chartContainerRef} className="flex-1 w-full h-full rounded-lg overflow-hidden" />
                </div>

                {/* RIGHT COL: EXECUTION & POSITIONS */}
                <div className="col-span-3 flex flex-col gap-4">
                    {/* ORDER ENTRY */}
                    <div className="glass-panel p-5 rounded-xl">
                        <h2 className="text-gray-400 text-xs tracking-wider mb-4">EXECUTION</h2>

                        <div className="flex gap-2 mb-4">
                            <button
                                onClick={() => setOrderSide('buy')}
                                className={`flex-1 py-2 rounded-lg font-bold transition-all ${orderSide === 'buy' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50 shadow-[0_0_15px_rgba(6,182,212,0.2)]' : 'bg-white/5 text-gray-500 hover:bg-white/10'}`}
                            >
                                BUY
                            </button>
                            <button
                                onClick={() => setOrderSide('sell')}
                                className={`flex-1 py-2 rounded-lg font-bold transition-all ${orderSide === 'sell' ? 'bg-pink-500/20 text-pink-400 border border-pink-500/50 shadow-[0_0_15px_rgba(236,72,153,0.2)]' : 'bg-white/5 text-gray-500 hover:bg-white/10'}`}
                            >
                                SELL
                            </button>
                        </div>

                        <div className="space-y-2 mb-4">
                            <input
                                type="number"
                                placeholder="Quantity"
                                value={orderQty}
                                onChange={e => setOrderQty(e.target.value)}
                                className="glass-input w-full p-2 rounded-lg text-sm"
                            />
                            <input
                                type="number"
                                placeholder="Limit Price (Optional)"
                                value={orderLimit}
                                onChange={e => setOrderLimit(e.target.value)}
                                className="glass-input w-full p-2 rounded-lg text-sm"
                            />
                        </div>

                        <button
                            onClick={handleOrder}
                            className="w-full py-3 bg-white/10 hover:bg-white/20 border border-white/20 rounded-lg font-bold tracking-widest transition-all hover:scale-[1.02] active:scale-95"
                        >
                            TRANSMIT
                        </button>
                    </div>

                    {/* POSITIONS & SCANNER */}
                    <div className="glass-panel p-5 rounded-xl flex-1 overflow-hidden flex flex-col gap-4">

                        {/* QUANTUM SCANNER */}
                        <div className="flex-1 flex flex-col min-h-0">
                            <h2 className="text-cyan-400 text-xs tracking-wider mb-2 flex items-center gap-2">
                                <Activity size={12} className="animate-pulse" /> QUANTUM SCANNER
                            </h2>
                            <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
                                {scanner.length === 0 && <div className="text-gray-600 text-xs italic">Scanning Field...</div>}
                                {scanner.map((c, idx) => (
                                    <div key={idx} className="bg-white/5 p-2 rounded border border-white/5 hover:border-cyan-500/30 transition-all cursor-pointer group">
                                        <div className="flex justify-between items-center mb-1">
                                            <span className="font-bold text-white group-hover:text-cyan-400 transition-colors">{c.symbol}</span>
                                            <span className="text-xs font-mono text-gray-400">${c.price.toFixed(2)}</span>
                                        </div>
                                        <div className="flex justify-between items-center text-[10px] text-gray-500">
                                            <div className="flex gap-2">
                                                <span>H: <span className="text-gray-300">{c.hurst.toFixed(2)}</span></span>
                                                <span>Vol: <span className="text-gray-300">{(c.volatility * 100).toFixed(1)}%</span></span>
                                            </div>
                                            <div className="flex items-center gap-1 text-cyan-500">
                                                <Zap size={10} />
                                                {(c.signal_potential * 100).toFixed(0)}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* POSITIONS */}
                        <div className="border-t border-white/10 pt-4 flex-1 flex flex-col min-h-0">
                            <h2 className="text-gray-400 text-xs tracking-wider mb-2">POSITIONS</h2>
                            <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
                                {positions.length === 0 && <div className="text-center text-gray-600 text-xs mt-4">NO POSITIONS</div>}
                                {positions.map((p, idx) => (
                                    <div key={idx} className="bg-white/5 p-3 rounded-lg border border-white/5 hover:border-white/10 transition-all">
                                        <div className="flex justify-between items-center mb-1">
                                            <span className="font-bold">{p.symbol}</span>
                                            <span className={`text-xs font-bold ${p.unrealized_pl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                ${p.unrealized_pl.toFixed(2)}
                                            </span>
                                        </div>
                                        <div className="flex justify-between text-xs text-gray-500">
                                            <span>{p.qty.toFixed(4)} UNITS</span>
                                            <span>@ {p.avg_entry_price.toFixed(2)}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* --- LOGS --- */}
            <div className="h-32 glass-panel rounded-xl p-3 font-mono text-xs overflow-y-auto w-full">
                <div className="text-gray-500 mb-2 sticky top-0 bg-[#0D1117]/90 p-1 flex items-center gap-2">
                    <Terminal size={12} /> SYSTEM LOGS
                </div>
                <div className="space-y-1">
                    {logs.map((log, i) => (
                        <div key={i} className="text-gray-400 border-l-2 border-white/10 pl-2">{log}</div>
                    ))}
                    <div ref={logsEndRef} />
                </div>
            </div>
        </div>
    );
};

export default ProTerminal;
