import React, { useState, useEffect, useRef } from 'react';

// Types for Logs
type LogType = 'INFO' | 'WARNING' | 'SUCCESS' | 'ERROR';

interface LogMessage {
    id: number;
    timestamp: string;
    type: LogType;
    message: string;
    // Metadata for inspection
    alpha?: number;
    sentiment_score?: number;
    sentiment_headline?: string;
    risk_size?: string;
    symbol?: string;
    side?: 'BUY' | 'SELL';
    price?: number;
}

interface AgentMonitorProps {
    onLogClick?: (log: LogMessage) => void;
}

const AgentMonitor: React.FC<AgentMonitorProps> = ({ onLogClick }) => {
    const [logs, setLogs] = useState<LogMessage[]>([]);
    const logsEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    const scrollToBottom = () => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [logs]);

    // Mock Data Generators
    const generateMockLog = (): LogMessage => {
        const types: LogType[] = ['INFO', 'INFO', 'INFO', 'WARNING', 'SUCCESS', 'INFO'];
        const messages = [
            "Alpha updated to 2.4",
            "Calculated Market Regime: GAUSSIAN",
            "RISK CHECK: Approved trade size $1,250",
            "PHYSICS VETO: Alpha < 2.0, Trade Blocked",
            "EXECUTION: Sent BUY order for NVDA",
            "Sleeping for 100ms...",
            "Analyzing market depth...",
            "Chronos Forecast: +1.2% confidence",
            "RISK ALERT: Drawdown limit approached"
        ];

        const randomType = types[Math.floor(Math.random() * types.length)];
        const randomMsg = messages[Math.floor(Math.random() * messages.length)];

        // Add mock metadata for inspection
        const isExecution = randomMsg.includes('EXECUTION');
        const isRisk = randomMsg.includes('RISK');
        const isPhysics = randomMsg.includes('PHYSICS');

        const mockMeta = (isExecution || isRisk || isPhysics) ? {
            alpha: Math.random() * 4,
            sentiment_score: (Math.random() * 2) - 1,
            sentiment_headline: "Tech sector rallies on AI chip demand...",
            risk_size: `${(Math.random() * 20).toFixed(1)}%`,
            symbol: "NVDA",
            side: Math.random() > 0.5 ? 'BUY' : 'SELL',
            price: 452.30
        } : {};

        return {
            id: Date.now(),
            timestamp: new Date().toLocaleTimeString(),
            type: randomType,
            message: randomMsg,
            ...mockMeta
        } as LogMessage;
    };

    // Simulation Effect
    useEffect(() => {
        const interval = setInterval(() => {
            const newLog = generateMockLog();
            setLogs((prevLogs) => {
                // Keep only last 100 logs to prevent memory overflow
                const updatedLogs = [...prevLogs, newLog];
                if (updatedLogs.length > 100) return updatedLogs.slice(updatedLogs.length - 100);
                return updatedLogs;
            });
        }, 2000); // Every 2 seconds

        return () => clearInterval(interval);
    }, []);

    // Helpers for styling
    const getTypeColor = (type: LogType) => {
        switch (type) {
            case 'SUCCESS': return 'text-green-400';
            case 'WARNING': return 'text-yellow-400';
            case 'ERROR': return 'text-red-500';
            default: return 'text-gray-300';
        }
    };

    const highlightKeywords = (text: string) => {
        // Simple parsing to highlight specific system components
        const riskRegex = /(RISK)/g;
        const physicsRegex = /(PHYSICS)/g;
        const executionRegex = /(EXECUTION)/g;

        let parts = text.split(/(RISK|PHYSICS|EXECUTION)/g);

        return parts.map((part, index) => {
            if (part === 'RISK') return <span key={index} className="text-red-500 font-bold">RISK</span>;
            if (part === 'PHYSICS') return <span key={index} className="text-blue-400 font-bold">PHYSICS</span>;
            if (part === 'EXECUTION') return <span key={index} className="text-purple-400 font-bold">EXECUTION</span>;
            return part;
        });
    };

    return (
        <div className="flex flex-col h-full bg-black text-xs font-mono border border-gray-800 rounded-md overflow-hidden shadow-lg">
            {/* Header */}
            <div className="bg-gray-900 px-4 py-2 border-b border-gray-800 flex justify-between items-center">
                <h3 className="text-gray-100 font-bold uppercase tracking-wider">System Logs</h3>
                <span className="flex items-center gap-2">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                    </span>
                    <span className="text-gray-400 text-[10px]">LIVE</span>
                </span>
            </div>

            {/* Log Feed */}
            <div className="flex-1 overflow-y-auto p-4 space-y-1 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
                {logs.length === 0 && (
                    <div className="text-gray-600 text-center mt-10 italic">Waiting for agents...</div>
                )}
                {logs.map((log) => (
                    <div
                        key={log.id}
                        className={`flex gap-3 hover:bg-gray-900/50 p-1 rounded transition-colors ${onLogClick ? 'cursor-pointer hover:bg-slate-800/50 active:bg-slate-800' : ''}`}
                        onClick={() => onLogClick && onLogClick(log)}
                    >
                        <span className="text-gray-500 min-w-[60px]">{log.timestamp}</span>
                        <span className={`font-bold min-w-[60px] ${getTypeColor(log.type)}`}>
                            [{log.type}]
                        </span>
                        <span className="text-gray-300 break-all">
                            {highlightKeywords(log.message)}
                        </span>
                    </div>
                ))}
                <div ref={logsEndRef} />
            </div>
        </div>
    );
};

export default AgentMonitor;
