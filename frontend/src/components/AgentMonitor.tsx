import React, { useEffect, useRef } from 'react';

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
    logs: any[]; // Telemetry packets from WebSocket
    onLogClick?: (log: any) => void;
}

const AgentMonitor: React.FC<AgentMonitorProps> = ({ logs, onLogClick }) => {
    const scrollContainerRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom using scrollTop to avoid page jumping
    const scrollToBottom = () => {
        if (scrollContainerRef.current) {
            const { scrollHeight, clientHeight } = scrollContainerRef.current;
            scrollContainerRef.current.scrollTop = scrollHeight - clientHeight;
        }
    };

    useEffect(() => {
        scrollToBottom();
    }, [logs]);

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
        const parts = text.split(/(RISK|PHYSICS|EXECUTION)/g);

        return parts.map((part, index) => {
            if (part === 'RISK') return <span key={index} className="text-red-500 font-bold">RISK</span>;
            if (part === 'PHYSICS') return <span key={index} className="text-blue-400 font-bold">PHYSICS</span>;
            if (part === 'EXECUTION') return <span key={index} className="text-purple-400 font-bold">EXECUTION</span>;
            return part;
        });
    };

    // Transform telemetry packet to log format
    const formatLogEntry = (packet: any, index: number) => {
        const timestamp = new Date(packet.timestamp || Date.now()).toLocaleTimeString();
        const signal = packet.signal?.side || 'FLAT';
        const reasoning = packet.signal?.reasoning || 'Processing...';

        return {
            id: index,
            timestamp,
            type: 'INFO' as LogType,
            message: `${signal}: ${reasoning.substring(0, 80)}...`,
            ...packet
        };
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
            <div
                ref={scrollContainerRef}
                className="flex-1 overflow-y-auto p-4 space-y-1 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent"
            >
                {logs.length === 0 && (
                    <div className="text-gray-600 text-center mt-10 italic">Waiting for agents...</div>
                )}
                {logs.map((packet, index) => {
                    const log = formatLogEntry(packet, index);
                    return (
                        <div
                            key={log.id}
                            className={`flex gap-3 hover:bg-gray-900/50 p-1 rounded transition-colors ${onLogClick ? 'cursor-pointer hover:bg-slate-800/50 active:bg-slate-800' : ''}`}
                            onClick={() => onLogClick && onLogClick(packet)}
                        >
                            <span className="text-gray-500 min-w-[60px]">{log.timestamp}</span>
                            <span className={`font-bold min-w-[60px] ${getTypeColor(log.type)}`}>
                                [{log.type}]
                            </span>
                            <span className="text-gray-300 break-all">
                                {highlightKeywords(log.message)}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default AgentMonitor;
