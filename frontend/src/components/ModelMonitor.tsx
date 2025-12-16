import React, { useState, useEffect } from 'react';
import { Brain, Activity, Zap } from 'lucide-react';

interface ModelMetric {
    name: string;
    latency: number;
    history: number[];
    status: 'OK' | 'DEGRADED' | 'DOWN';
}

const ModelMonitor: React.FC = () => {
    const [models, setModels] = useState<ModelMetric[]>([
        { name: 'FinBERT', latency: 120, history: [120, 115, 125, 118, 122, 119, 121, 124, 118, 120], status: 'OK' },
        { name: 'Chronos', latency: 450, history: [410, 420, 435, 440, 425, 430, 445, 450, 448, 450], status: 'DEGRADED' },
        { name: 'Gemma2', latency: 85, history: [80, 82, 85, 83, 81, 84, 86, 82, 85, 85], status: 'OK' },
    ]);

    useEffect(() => {
        const interval = setInterval(() => {
            setModels(prev => prev.map(model => {
                // Simulate latency fluctuation
                const change = Math.floor(Math.random() * 20) - 10;
                const newLatency = Math.max(20, model.latency + change);

                let status: 'OK' | 'DEGRADED' | 'DOWN' = 'OK';
                if (newLatency > 500) status = 'DOWN';
                else if (newLatency > 200) status = 'DEGRADED';

                const newHistory = [...model.history.slice(1), newLatency];

                return {
                    ...model,
                    latency: newLatency,
                    history: newHistory,
                    status
                };
            }));
        }, 1000);

        return () => clearInterval(interval);
    }, []);

    const getStatusColor = (status: string, latency: number) => {
        if (status === 'DOWN' || latency > 1000) return 'text-red-500 bg-red-500/10 border-red-500/30';
        if (status === 'DEGRADED' || latency > 200) return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30';
        return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30';
    };

    const renderSparkline = (data: number[], colorClass: string) => {
        const min = Math.min(...data);
        const max = Math.max(...data);
        const range = max - min || 1;
        const height = 20;
        const width = 60;
        const step = width / (data.length - 1);

        const points = data.map((val, i) => {
            const x = i * step;
            const y = height - ((val - min) / range) * height;
            return `${x},${y}`;
        }).join(' ');

        // Extract color hex roughly from tailwind class or use currentcolor
        // Ideally we pass specific hex, but here we let SVG inherit or use generic
        return (
            <svg width={width} height={height} className="opacity-50 overflow-visible">
                <polyline
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    points={points}
                    vectorEffect="non-scaling-stroke"
                />
            </svg>
        );
    };

    return (
        <div className="flex gap-4 w-full h-full">
            {models.map((model) => {
                const styleClass = getStatusColor(model.status, model.latency);

                return (
                    <div key={model.name} className={`flex-1 flex flex-col justify-between p-3 rounded-lg border ${styleClass} transition-all duration-300`}>

                        <div className="flex justify-between items-start">
                            <div className="flex items-center gap-2">
                                {model.name === 'FinBERT' && <Activity size={16} />}
                                {model.name === 'Chronos' && <Zap size={16} />}
                                {model.name === 'Gemma2' && <Brain size={16} />}
                                <span className="font-bold text-xs uppercase tracking-wider">{model.name}</span>
                            </div>
                            <div className="flex flex-col items-end">
                                <span className="text-sm font-mono font-bold">{model.latency}ms</span>
                                <span className="text-[10px] opacity-70">{model.status}</span>
                            </div>
                        </div>

                        <div className="mt-2 text-right">
                            {renderSparkline(model.history, styleClass)}
                        </div>

                    </div>
                );
            })}
        </div>
    );
};

export default ModelMonitor;
