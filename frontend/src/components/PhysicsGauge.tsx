import React, { useState, useEffect } from 'react';
import { Gauge, Zap, TrendingUp, WifiOff } from 'lucide-react';

interface PhysicsMetrics {
    alpha: number;
    velocity: number;
    acceleration: number;
    regime: string;
    timestamp: string | null;
}

const PhysicsGauge: React.FC = () => {
    const [metrics, setMetrics] = useState<PhysicsMetrics>({
        alpha: 3.0,
        velocity: 0.0,
        acceleration: 0.0,
        regime: 'Unknown',
        timestamp: null,
    });
    const [isOffline, setIsOffline] = useState(false);

    useEffect(() => {
        const fetchPhysics = async () => {
            try {
                // Use /api proxy for production, direct URL for dev
                const response = await fetch('/api/system/status/physics');

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                setMetrics(data);
                setIsOffline(false);
            } catch (error) {
                console.warn('Physics API unavailable, using last known values:', error);
                setIsOffline(true);
                // Retain last known values (ghost mode)
            }
        };

        // Initial fetch
        fetchPhysics();

        // Poll every 1000ms
        const interval = setInterval(fetchPhysics, 1000);

        return () => clearInterval(interval);
    }, []);

    const { alpha, velocity, acceleration } = metrics;

    // Determine Zone
    const normalizedAlpha = Math.min(Math.max(alpha, 0), 4);
    const percentage = (normalizedAlpha / 4) * 100;

    const isSafe = alpha > 3.0; // Standard Gaussian
    const isDanger = alpha < 2.0; // Levy Regime (Infinite Variance)

    const barColor = isDanger ? 'bg-destructive' : (isSafe ? 'bg-green-500' : 'bg-yellow-500');
    const statusText = isDanger ? 'CRITICAL (Lévy)' : (isSafe ? 'STABLE (Gaussian)' : 'CAUTION');

    return (
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
            {/* Offline Indicator */}
            {isOffline && (
                <div className="absolute top-2 right-2 flex items-center gap-1 text-xs text-muted-foreground bg-background/80 px-2 py-1 rounded-full border border-border">
                    <WifiOff className="w-3 h-3" />
                    OFFLINE
                </div>
            )}

            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <Gauge className="w-24 h-24 text-primary" />
            </div>

            <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <Gauge className="w-5 h-5 text-primary" />
                Physics Engine
            </h2>

            {/* Alpha Gauge */}
            <div className="mb-8">
                <div className="flex justify-between items-end mb-2">
                    <span className="text-sm text-muted-foreground font-mono">ALPHA (TAIL INDEX)</span>
                    <span className={`text-3xl font-bold font-mono ${isDanger ? 'text-destructive' : 'text-foreground'}`}>
                        {alpha.toFixed(2)}
                    </span>
                </div>

                {/* Bar */}
                <div className="h-4 w-full bg-secondary rounded-full overflow-hidden relative">
                    {/* Zones Markers */}
                    <div className="absolute left-[50%] h-full w-0.5 bg-background z-10 opacity-50" title="2.0"></div>
                    <div className="absolute left-[75%] h-full w-0.5 bg-background z-10 opacity-50" title="3.0"></div>

                    <div
                        className={`h-full ${barColor} transition-all duration-500 ease-out`}
                        style={{ width: `${percentage}%` }}
                    />
                </div>
                <div className="flex justify-between text-xs text-muted-foreground mt-1 font-mono">
                    <span>0.0</span>
                    <span className="text-destructive font-bold">&lt; 2.0 Danger</span>
                    <span>2.0</span>
                    <span className="text-green-500 font-bold">&gt; 3.0 Safe</span>
                    <span>4.0</span>
                </div>
                <div className={`mt-2 text-center text-sm font-bold ${isDanger ? 'text-destructive' : 'text-foreground'}`}>
                    STATUS: {statusText}
                </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 gap-4">
                <div className="bg-background/50 p-4 rounded-lg border border-border">
                    <div className="flex items-center gap-2 mb-1 text-muted-foreground text-xs">
                        <Zap className="w-3 h-3" />
                        VELOCITY
                    </div>
                    <div className="text-xl font-mono font-bold text-foreground">
                        {velocity.toFixed(4)}
                    </div>
                </div>
                <div className="bg-background/50 p-4 rounded-lg border border-border">
                    <div className="flex items-center gap-2 mb-1 text-muted-foreground text-xs">
                        <TrendingUp className="w-3 h-3" />
                        ACCELERATION
                    </div>
                    <div className="text-xl font-mono font-bold text-foreground">
                        {acceleration.toFixed(4)}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default PhysicsGauge;
