import React from 'react';
import { X, Activity, Brain, Shield, Clock } from 'lucide-react';

interface AutopsyData {
    alpha: number;
    sentiment_score: number;
    sentiment_headline: string;
    risk_size: string; // e.g. "12.5%"
    timestamp: string;
    symbol: string;
    side: 'BUY' | 'SELL';
    price?: number;
}

interface AutopsyPanelProps {
    isOpen: boolean;
    onClose: () => void;
    data: AutopsyData | null;
}

const AutopsyPanel: React.FC<AutopsyPanelProps> = ({ isOpen, onClose, data }) => {
    if (!isOpen || !data) return null;

    const isSafeAlpha = data.alpha > 3.0;
    const isDangerAlpha = data.alpha < 2.0;
    const alphaColor = isSafeAlpha ? 'text-emerald-400' : isDangerAlpha ? 'text-red-500' : 'text-yellow-400';

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/80 backdrop-blur-sm transition-opacity duration-300"
                onClick={onClose}
            ></div>

            {/* Modal Content */}
            <div className="relative bg-slate-900/90 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden animate-in fade-in zoom-in duration-200">

                {/* Header */}
                <div className="bg-slate-950 p-6 flex justify-between items-start border-b border-slate-800">
                    <div>
                        <h2 className="text-3xl font-black text-slate-100 tracking-wider">
                            {data.side} <span className="text-emerald-500">{data.symbol}</span>
                        </h2>
                        <p className="text-slate-500 text-sm font-mono mt-1">TRADE INSPECTION</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400 hover:text-white"
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* The Grid (2x2) */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-slate-800/50">

                    {/* Quadrant 1: Physics */}
                    <div className="bg-slate-900/95 p-6 flex flex-col gap-2 hover:bg-slate-900 transition-colors group">
                        <div className="flex items-center gap-2 text-slate-400 mb-2">
                            <Activity size={18} />
                            <span className="text-xs font-bold uppercase tracking-widest">Physics Alpha</span>
                        </div>
                        <div className={`text-4xl font-mono font-bold ${alphaColor}`}>
                            {data.alpha.toFixed(2)}
                        </div>
                        <p className="text-xs text-slate-500">
                            {isSafeAlpha
                                ? "Stable Regime. Heavy tails absent."
                                : isDangerAlpha
                                    ? "CRITICAL: Infinite Variance Detected."
                                    : "Caution: Approaching phase transition."}
                        </p>
                    </div>

                    {/* Quadrant 2: Brain (Sentiment) */}
                    <div className="bg-slate-900/95 p-6 flex flex-col gap-2 hover:bg-slate-900 transition-colors group">
                        <div className="flex items-center gap-2 text-slate-400 mb-2">
                            <Brain size={18} />
                            <span className="text-xs font-bold uppercase tracking-widest">Sentiment Core</span>
                        </div>
                        <div className="flex items-baseline gap-2">
                            <span className={`text-4xl font-mono font-bold ${data.sentiment_score > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                {data.sentiment_score > 0 ? '+' : ''}{data.sentiment_score}
                            </span>
                            <span className="text-xs text-slate-500 font-bold uppercase">Score</span>
                        </div>
                        <p className="text-sm text-slate-300 italic font-serif leading-relaxed border-l-2 border-slate-700 pl-3 mt-1">
                            "{data.sentiment_headline}"
                        </p>
                    </div>

                    {/* Quadrant 3: Shield (Risk Size) */}
                    <div className="bg-slate-900/95 p-6 flex flex-col gap-2 hover:bg-slate-900 transition-colors group">
                        <div className="flex items-center gap-2 text-slate-400 mb-2">
                            <Shield size={18} />
                            <span className="text-xs font-bold uppercase tracking-widest">Approved Sizing</span>
                        </div>
                        <div className="text-4xl font-mono font-bold text-blue-400">
                            {data.risk_size}
                        </div>
                        <p className="text-xs text-slate-500">
                            Computed via Fractional Kelly & Volatility Scaling.
                        </p>
                    </div>

                    {/* Quadrant 4: Execution (Time) */}
                    <div className="bg-slate-900/95 p-6 flex flex-col gap-2 hover:bg-slate-900 transition-colors group">
                        <div className="flex items-center gap-2 text-slate-400 mb-2">
                            <Clock size={18} />
                            <span className="text-xs font-bold uppercase tracking-widest">Execution Time</span>
                        </div>
                        <div className="text-2xl font-mono text-slate-200">
                            {data.timestamp}
                        </div>
                        {data.price && (
                            <div className="mt-auto pt-2 border-t border-slate-800 flex justify-between items-center text-sm">
                                <span className="text-slate-500">Info Price</span>
                                <span className="font-mono text-emerald-400">${data.price}</span>
                            </div>
                        )}
                    </div>

                </div>

            </div>
        </div>
    );
};

export default AutopsyPanel;
