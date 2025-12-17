import React, { useState, useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, CandlestickData } from 'lightweight-charts';

interface Position {
    symbol: string;
    qty: number;
    avg_entry_price: number;
    unrealized_pl: number;
}

interface TelemetryPacket {
    market?: {
        price?: number;
        alpha?: number;
        velocity?: number;
        history?: any[];
    };
    signal?: {
        side?: string;
        confidence?: number;
        reasoning?: string;
        strategy?: string;
    };
}

const ProTerminal: React.FC = () => {
    const [isConnected, setIsConnected] = useState<boolean>(false);
    const [systemMode, setSystemMode] = useState<string>('PAPER'); // PAPER or LIVE
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

    // Order Entry State
    const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy');
    const [orderQty, setOrderQty] = useState<string>('');
    const [orderLimit, setOrderLimit] = useState<string>('');

    // Data State
    const [positions, setPositions] = useState<Position[]>([]);
    const [telemetry, setTelemetry] = useState<TelemetryPacket | null>(null);

    // Fetch positions
    const fetchPositions = async () => {
        try {
            const res = await fetch('http://localhost:8000/api/orders/positions');
            const data = await res.json();
            setPositions(data);
        } catch (error) {
            console.error('Failed to fetch positions:', error);
        }
    };

    // Initial fetch and poll
    useEffect(() => {
        fetchPositions();
        const interval = setInterval(fetchPositions, 5000); // Poll every 5s
        return () => clearInterval(interval);
    }, []);

    // WebSocket connection
    useEffect(() => {
        const WS_URL = 'ws://localhost:8000/api/ws/stream';
        let ws: WebSocket | null = null;

        const connect = () => {
            ws = new WebSocket(WS_URL);
            ws.onopen = () => {
                console.log('✅ WebSocket Connected');
                setIsConnected(true);
            };
            ws.onmessage = (event: MessageEvent) => {
                try {
                    const packet = JSON.parse(event.data);
                    setTelemetry(packet);

                    if (packet.market && packet.market.history && candleSeriesRef.current) {
                        // Update Chart if we have history
                        // We expect history to be a list of dicts with { close, open, high, low, timestamp }
                        const rawHistory = packet.market.history;

                        if (Array.isArray(rawHistory) && rawHistory.length > 0) {
                            const formattedData: CandlestickData[] = rawHistory.map((bar: any) => ({
                                time: bar.timestamp ? bar.timestamp.split('T')[0] : '2024-01-01', // ISO to YYYY-MM-DD for visual
                                open: bar.open,
                                high: bar.high,
                                low: bar.low,
                                close: bar.close
                            }))
                                .filter((bar: any) => bar.time) // Ensure time exists
                                // Deduplicate by time
                                .reduce((acc: CandlestickData[], current: CandlestickData) => {
                                    const x = acc.find(item => item.time === current.time);
                                    if (!x) {
                                        return acc.concat([current]);
                                    } else {
                                        return acc;
                                    }
                                }, [])
                                .sort((a: any, b: any) => (new Date(a.time).getTime()) - (new Date(b.time).getTime()));

                            if (formattedData.length > 0) {
                                candleSeriesRef.current.setData(formattedData);
                            }
                        }
                    }
                } catch (e) {
                    console.error("Error parsing telemetry:", e);
                }
            };
            ws.onclose = () => {
                setIsConnected(false);
                setTimeout(connect, 5000);
            };
        };

        connect();
        return () => {
            if (ws) ws.close();
        };
    }, []);

    // Initialize TradingView Chart
    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            width: chartContainerRef.current.clientWidth,
            height: 500,
            layout: {
                backgroundColor: '#0A0E14',
                textColor: '#E5E9F0',
            },
            grid: {
                vertLines: { color: '#1C2128' },
                horzLines: { color: '#1C2128' },
            },
            crosshair: {
                mode: 1,
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
            upColor: '#A3BE8C',
            downColor: '#BF616A',
            borderDownColor: '#BF616A',
            borderUpColor: '#A3BE8C',
            wickDownColor: '#BF616A',
            wickUpColor: '#A3BE8C',
        });

        candleSeriesRef.current = candlestickSeries;
        chartRef.current = chart;

        // Resize handler
        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({
                    width: chartContainerRef.current.clientWidth,
                });
            }
        };

        window.addEventListener('resize', handleResize);
        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, []);

    const handleHalt = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/actions/halt', {
                method: 'POST',
            });
            const result = await response.json();
            alert(result.message);
        } catch (error: any) {
            alert('Failed to halt: ' + error.message);
        }
    };

    const handleOrder = async () => {
        if (!orderQty) return;
        try {
            const res = await fetch('http://localhost:8000/api/orders/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: 'SPY', // Hardcoded for now
                    qty: parseFloat(orderQty),
                    side: orderSide,
                    type: orderLimit ? 'limit' : 'market',
                    limit_price: orderLimit ? parseFloat(orderLimit) : null
                })
            });
            const data = await res.json();
            if (data.success) {
                alert(`Order Submitted: ${data.message}`);
                setOrderQty('');
                fetchPositions(); // Refresh positions
            } else {
                alert(`Order Failed: ${data.message}`);
            }
        } catch (error: any) {
            alert(`Error: ${error.message}`);
        }
    };

    // Derived values for UI
    const price = telemetry?.market?.price || 0.00;
    const signal = telemetry?.signal?.side || 'FLAT';
    const confidence = telemetry?.signal?.confidence || 0.00;
    const alpha = telemetry?.market?.alpha || 0.00;
    const velocity = telemetry?.market?.velocity || 0.0000;
    const activeStrategy = telemetry?.signal?.strategy || 'None';

    return (
        <div className="h-screen bg-[#0A0E14] text-[#E5E9F0] font-mono flex flex-col overflow-hidden">
            {/* TOP BAR */}
            <header className="h-12 bg-[#0D1117] border-b border-[#1C2128] flex items-center justify-between px-4">
                <div className="flex items-center gap-4">
                    <div className="text-sm font-bold tracking-wider">
                        CURIOSITY <span className="text-[#88C0D0]">v2.0</span>
                    </div>
                    <div className="text-xs text-[#88C0D0]">SPY</div>
                    <div className="text-sm font-bold">${price.toFixed(2)}</div>
                    {/* <div className="text-xs text-[#A3BE8C]">+0.45%</div> */}
                </div>

                <div className="flex items-center gap-4">
                    {/* Connection Status */}
                    <div className="flex items-center gap-2">
                        <div
                            className={`w-2 h-2 rounded-full ${isConnected ? 'bg-[#A3BE8C]' : 'bg-[#BF616A]'
                                }`}
                        ></div>
                        <span className="text-xs">
                            {isConnected ? 'LIVE' : 'OFFLINE'}
                        </span>
                    </div>

                    {/* Mode Indicator */}
                    <div
                        className={`px-3 py-1 rounded text-xs font-bold ${systemMode === 'PAPER'
                            ? 'bg-[#EBCB8B] text-[#0A0E14]'
                            : 'bg-[#BF616A] text-white'
                            }`}
                    >
                        {systemMode === 'PAPER' ? '📄 PAPER TRADING' : '🔴 LIVE TRADING'}
                    </div>

                    {/* Halt Button */}
                    <button
                        onClick={handleHalt}
                        className="px-3 py-1 bg-[#BF616A] hover:bg-[#D08770] text-white text-xs font-bold rounded transition"
                    >
                        EMERGENCY HALT
                    </button>
                </div>
            </header>

            {/* MAIN GRID */}
            <div className="flex-1 grid grid-cols-12 gap-0.5 bg-[#1C2128] overflow-hidden">
                {/* LEFT PANEL: Watchlist + Positions */}
                <div className="col-span-2 bg-[#0A0E14] flex flex-col overflow-hidden">
                    {/* Watchlist */}
                    <div className="flex-1 border-b border-[#1C2128] p-3 overflow-y-auto">
                        <div className="text-xs font-bold text-[#88C0D0] mb-2">WATCHLIST</div>
                        <div className="space-y-1">
                            <div className="p-2 bg-[#0D1117] rounded text-xs cursor-pointer hover:bg-[#161B22]">
                                <div className="flex justify-between">
                                    <span className="font-bold">SPY</span>
                                    {/* <span className="text-[#A3BE8C]">+0.45%</span> */}
                                </div>
                                <div className="text-[#6B7280]">${price.toFixed(2)}</div>
                            </div>
                        </div>
                    </div>

                    {/* Positions */}
                    <div className="flex-1 p-3 overflow-y-auto">
                        <div className="text-xs font-bold text-[#88C0D0] mb-2">POSITIONS</div>
                        {positions.length === 0 ? (
                            <div className="text-xs text-[#6B7280] text-center py-8">
                                No positions
                            </div>
                        ) : (
                            <div className="space-y-1">
                                {positions.map((pos, idx) => (
                                    <div key={idx} className="p-2 bg-[#0D1117] rounded text-xs border border-[#1C2128]">
                                        <div className="flex justify-between font-bold">
                                            <span>{pos.symbol}</span>
                                            <span className={pos.unrealized_pl >= 0 ? "text-[#A3BE8C]" : "text-[#BF616A]"}>
                                                ${pos.unrealized_pl.toFixed(2)}
                                            </span>
                                        </div>
                                        <div className="flex justify-between text-[#6B7280] mt-1">
                                            <span>{pos.qty} sh</span>
                                            <span>@ {pos.avg_entry_price.toFixed(2)}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* CENTER PANEL: Chart + Order Entry */}
                <div className="col-span-7 bg-[#0A0E14] flex flex-col">
                    {/* Chart */}
                    <div className="flex-1 p-3 relative">
                        {/* Chart Legend/Status Overlay */}
                        <div className="absolute top-4 left-4 z-10 text-[10px] text-[#88C0D0] bg-[#0A0E14]/80 p-1 rounded border border-[#1C2128]">
                            Strategy: {activeStrategy}<br />
                            Signal: {signal} ({confidence.toFixed(2)})
                        </div>
                        <div ref={chartContainerRef} className="w-full h-full" />
                    </div>

                    {/* Order Entry */}
                    <div className="h-40 border-t border-[#1C2128] p-3">
                        <div className="text-xs font-bold text-[#88C0D0] mb-2">ORDER ENTRY</div>
                        <div className="flex gap-2 items-center">
                            <div className="flex bg-[#0D1117] rounded overflow-hidden mr-4">
                                <button
                                    onClick={() => setOrderSide('buy')}
                                    className={`px-4 py-2 text-xs font-bold ${orderSide === 'buy' ? 'bg-[#A3BE8C] text-[#0A0E14]' : 'text-[#6B7280] hover:bg-[#161B22]'}`}
                                >
                                    BUY
                                </button>
                                <button
                                    onClick={() => setOrderSide('sell')}
                                    className={`px-4 py-2 text-xs font-bold ${orderSide === 'sell' ? 'bg-[#BF616A] text-white' : 'text-[#6B7280] hover:bg-[#161B22]'}`}
                                >
                                    SELL
                                </button>
                            </div>

                            <input
                                type="number"
                                placeholder="Qty"
                                value={orderQty}
                                onChange={(e) => setOrderQty(e.target.value)}
                                className="px-3 py-2 bg-[#0D1117] border border-[#1C2128] rounded text-xs w-20 focus:outline-none focus:border-[#88C0D0]"
                            />
                            <input
                                type="number"
                                placeholder="Limit $"
                                value={orderLimit}
                                onChange={(e) => setOrderLimit(e.target.value)}
                                className="px-3 py-2 bg-[#0D1117] border border-[#1C2128] rounded text-xs w-24 focus:outline-none focus:border-[#88C0D0]"
                            />
                            <button
                                onClick={handleOrder}
                                className="px-4 py-2 bg-[#88C0D0] text-[#0A0E14] text-xs font-bold rounded hover:bg-[#8FBCBB] ml-2"
                            >
                                SEND ORDER
                            </button>
                        </div>
                        <div className="mt-2 text-[10px] text-[#6B7280]">
                            Submitting {orderSide.toUpperCase()} {orderQty || 0} SPY {orderLimit ? `@ ${orderLimit}` : 'MKT'}
                        </div>
                    </div>
                </div>

                {/* RIGHT PANEL: Risk + Agent + Account */}
                <div className="col-span-3 bg-[#0A0E14] flex flex-col overflow-hidden">
                    {/* Risk Monitor */}
                    <div className="p-3 border-b border-[#1C2128]">
                        <div className="text-xs font-bold text-[#88C0D0] mb-2">RISK MONITOR</div>
                        <div className="space-y-2 text-xs">
                            <div className="flex justify-between">
                                <span className="text-[#6B7280]">Alpha:</span>
                                <span className="font-bold text-[#BF616A]">{alpha.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-[#6B7280]">Velocity:</span>
                                <span>{velocity.toFixed(4)}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-[#6B7280]">VaR 95%:</span>
                                <span>-$0</span>
                            </div>
                        </div>
                    </div>

                    {/* Agent Status */}
                    <div className="p-3 border-b border-[#1C2128]">
                        <div className="text-xs font-bold text-[#88C0D0] mb-2">AGENT STATUS</div>
                        <div className="space-y-1 text-xs">
                            <div className="flex justify-between">
                                <span className="text-[#6B7280]">Analyst:</span>
                                <span className="text-[#A3BE8C]">ACTIVE</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-[#6B7280]">Risk:</span>
                                <span className="text-[#6B7280]">IDLE</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-[#6B7280]">Execution:</span>
                                <span className="text-[#6B7280]">IDLE</span>
                            </div>
                        </div>
                    </div>

                    {/* Account Summary */}
                    <div className="p-3 border-b border-[#1C2128]">
                        <div className="text-xs font-bold text-[#88C0D0] mb-2">ACCOUNT</div>
                        <div className="space-y-2 text-xs">
                            <div className="flex justify-between">
                                <span className="text-[#6B7280]">Equity:</span>
                                <span className="font-bold">$100,000</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-[#6B7280]">Cash:</span>
                                <span>$100,000</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-[#6B7280]">Day P&L:</span>
                                <span className="text-[#6B7280]">$0.00</span>
                            </div>
                        </div>
                    </div>

                    {/* Signal Feed */}
                    <div className="flex-1 p-3 overflow-y-auto">
                        <div className="text-xs font-bold text-[#88C0D0] mb-2">SIGNAL FEED</div>
                        <div className="space-y-1 text-xs text-[#6B7280]">
                            {telemetry?.signal && (
                                <div className="p-2 bg-[#0D1117] rounded">
                                    <div className="font-bold">
                                        {new Date().toLocaleTimeString()} {telemetry.signal.side}
                                    </div>
                                    <div className="text-[10px]">{telemetry.signal.reasoning}</div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProTerminal;
