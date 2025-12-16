import React, { useState, useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

const ProTerminal = () => {
    const [isConnected, setIsConnected] = useState(false);
    const [systemMode, setSystemMode] = useState('PAPER'); // PAPER or LIVE
    const chartContainerRef = useRef(null);
    const chartRef = useRef(null);

    // WebSocket connection (same as Dashboard)
    useEffect(() => {
        const WS_URL = 'ws://localhost:8000/api/ws/stream';
        let ws = null;

        const connect = () => {
            ws = new WebSocket(WS_URL);
            ws.onopen = () => {
                console.log('✅ WebSocket Connected');
                setIsConnected(true);
            };
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                // TODO: Update chart and metrics
                console.log('Telemetry:', data);
            };
            ws.onclose = () => {
                setIsConnected(false);
                setTimeout(connect, 5000);
            };
        };

        connect();
        return () => ws && ws.close();
    }, []);

    // Initialize TradingView Chart
    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            width: chartContainerRef.current.clientWidth,
            height: 500,
            layout: {
                background: { color: '#0A0E14' },
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

        // Sample data (will be replaced with live data)
        candlestickSeries.setData([
            { time: '2024-12-16', open: 450, high: 455, low: 448, close: 453 },
            { time: '2024-12-17', open: 453, high: 457, low: 451, close: 455 },
        ]);

        chartRef.current = chart;

        // Resize handler
        const handleResize = () => {
            chart.applyOptions({
                width: chartContainerRef.current.clientWidth,
            });
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
        } catch (error) {
            alert('Failed to halt: ' + error.message);
        }
    };

    return (
        <div className="h-screen bg-[#0A0E14] text-[#E5E9F0] font-mono flex flex-col overflow-hidden">
            {/* TOP BAR */}
            <header className="h-12 bg-[#0D1117] border-b border-[#1C2128] flex items-center justify-between px-4">
                <div className="flex items-center gap-4">
                    <div className="text-sm font-bold tracking-wider">
                        CURIOSITY <span className="text-[#88C0D0]">v2.0</span>
                    </div>
                    <div className="text-xs text-[#88C0D0]">SPY</div>
                    <div className="text-sm font-bold">$453.21</div>
                    <div className="text-xs text-[#A3BE8C]">+0.45%</div>
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
                                    <span className="text-[#A3BE8C]">+0.45%</span>
                                </div>
                                <div className="text-[#6B7280]">$453.21</div>
                            </div>
                            <div className="p-2 rounded text-xs cursor-pointer hover:bg-[#161B22] text-[#6B7280]">
                                <div className="flex justify-between">
                                    <span>QQQ</span>
                                    <span>+0.22%</span>
                                </div>
                                <div>$387.50</div>
                            </div>
                        </div>
                    </div>

                    {/* Positions */}
                    <div className="flex-1 p-3 overflow-y-auto">
                        <div className="text-xs font-bold text-[#88C0D0] mb-2">POSITIONS</div>
                        <div className="text-xs text-[#6B7280] text-center py-8">
                            No positions
                        </div>
                    </div>
                </div>

                {/* CENTER PANEL: Chart + Order Entry */}
                <div className="col-span-7 bg-[#0A0E14] flex flex-col">
                    {/* Chart */}
                    <div className="flex-1 p-3">
                        <div ref={chartContainerRef} className="w-full h-full" />
                    </div>

                    {/* Order Entry */}
                    <div className="h-40 border-t border-[#1C2128] p-3">
                        <div className="text-xs font-bold text-[#88C0D0] mb-2">ORDER ENTRY</div>
                        <div className="flex gap-2">
                            <button className="px-4 py-2 bg-[#A3BE8C] text-[#0A0E14] text-xs font-bold rounded hover:bg-[#B5D19E]">
                                BUY
                            </button>
                            <button className="px-4 py-2 bg-[#BF616A] text-white text-xs font-bold rounded hover:bg-[#D08770]">
                                SELL
                            </button>
                            <input
                                type="number"
                                placeholder="Qty"
                                className="px-3 py-2 bg-[#0D1117] border border-[#1C2128] rounded text-xs w-20 focus:outline-none focus:border-[#88C0D0]"
                            />
                            <input
                                type="number"
                                placeholder="Limit $"
                                className="px-3 py-2 bg-[#0D1117] border border-[#1C2128] rounded text-xs w-24 focus:outline-none focus:border-[#88C0D0]"
                            />
                            <button className="px-4 py-2 bg-[#88C0D0] text-[#0A0E14] text-xs font-bold rounded hover:bg-[#8FBCBB]">
                                SEND
                            </button>
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
                                <span className="font-bold text-[#BF616A]">0.00</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-[#6B7280]">Velocity:</span>
                                <span>0.0000</span>
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
                            <div className="p-2 bg-[#0D1117] rounded">
                                <div className="font-bold">12:45 FLAT</div>
                                <div className="text-[10px]">LLM service unavailable</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProTerminal;
