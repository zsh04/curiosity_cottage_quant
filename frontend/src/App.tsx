import { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import PhysicsGauge from './components/PhysicsGauge';
import SentimentTriad from './components/SentimentTriad';
import AutopsyPanel from './components/AutopsyPanel';
import { AgentMonitor } from './components/AgentMonitor';
import { ModelMonitor } from './components/ModelMonitor';
import './index.css';

interface TelemetryData {
    timestamp: string;
    status: string;
    market: {
        symbol: string;
        price: number;
        alpha: number;
        regime: string;
        velocity?: number;
        acceleration?: number;
    };
    portfolio?: {
        nav: number;
        cash: number;
        daily_pnl: number;
        max_drawdown: number;
    };
    signal?: {
        side: string;
        confidence: number;
        reasoning: string;
    };
    sentiment: {
        label: string;
        score: number;
    };
    logs: string[];
    agents?: any;
    models?: any;
}

function App() {
    const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
    const [logs, setLogs] = useState<string[]>([]);
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Connect to BFF WebSocket
        const ws = new WebSocket('ws://localhost:3000');
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('Connected to BFF');
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'TELEMETRY' || msg.type === 'WELCOME') {
                    setTelemetry(msg.data);
                    // Accumulate logs (keep last 50)
                    if (msg.data.logs && msg.data.logs.length > 0) {
                        setLogs((prev) => [...msg.data.logs, ...prev].slice(0, 50));
                    }
                }
            } catch (e) {
                console.error('WS Parse Error:', e);
            }
        };

        ws.onerror = (err) => {
            console.error('WS Error:', err);
        };

        ws.onclose = () => {
            console.log('Disconnected from BFF');
        };

        return () => {
            ws.close();
        };
    }, []);

    const handleReset = async () => {
        try {
            await fetch('http://localhost:3000/trade/reset', { method: 'POST' });
            console.log('Reset triggered');
        } catch (e) {
            console.error('Reset failed:', e);
        }
    };

    const handleForceTrigger = async () => {
        try {
            await fetch('http://localhost:3000/trade/force', { method: 'POST' });
            console.log('Force trigger sent');
        } catch (e) {
            console.error('Force trigger failed:', e);
        }
    };

    if (!telemetry) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="text-muted-foreground">Connecting...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background">
            <Header
                symbol={telemetry.market.symbol}
                price={telemetry.market.price}
                regime={telemetry.market.regime}
                connection="Connected"
                systemStatus={telemetry.status}
            />

            <div className="container mx-auto px-6 py-8">
                {/* Top Row: Physics & Sentiment */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                    <PhysicsGauge
                        alpha={telemetry.market.alpha}
                        velocity={telemetry.market.velocity || 0}
                        acceleration={telemetry.market.acceleration || 0}
                    />
                    <SentimentTriad sentiment={telemetry.sentiment} />
                </div>

                {/* Middle Row: Agent & Model Performance */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                    <AgentMonitor agents={telemetry.agents || {}} />
                    <ModelMonitor models={telemetry.models || {}} />
                </div>

                {/* Bottom Row: Autopsy */}
                <AutopsyPanel logs={logs} />

                {/* Action Buttons */}
                <div className="mt-6 flex gap-4">
                    <button
                        onClick={handleReset}
                        className="px-4 py-2 bg-red-500/10 text-red-500 border border-red-500/30 rounded-md hover:bg-red-500/20 transition-colors"
                    >
                        Reset System
                    </button>
                    <button
                        onClick={handleForceTrigger}
                        className="px-4 py-2 bg-primary/10 text-primary border border-primary/30 rounded-md hover:bg-primary/20 transition-colors"
                    >
                        Force Trigger
                    </button>
                </div>
            </div>
        </div>
    );
}

export default App;
