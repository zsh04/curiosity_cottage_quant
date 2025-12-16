import React, { useState } from 'react';
import { Terminal, Search, X, AlertTriangle } from 'lucide-react';

interface LogMessage {
    role: string;
    content: string;
    timestamp?: string; // Optional if not provided by backend
}

interface AutopsyPanelProps {
    logs: LogMessage[];
}

const AutopsyPanel: React.FC<AutopsyPanelProps> = ({ logs }) => {
    const [selectedLog, setSelectedLog] = useState<LogMessage | null>(null);

    // Identify trade logs to show "View Autopsy" button
    const isTradeLog = (msg: LogMessage) => {
        return msg.content.includes('ORDER_FILLED') || msg.content.includes('SENT ORDER') || msg.content.includes('EXECUTION');
    };

    return (
        <div className="flex flex-col h-full bg-card border border-border rounded-xl shadow-sm overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-border flex justify-between items-center bg-muted/20">
                <div className="flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-primary" />
                    <h3 className="font-semibold text-sm font-mono">SYSTEM LOGS & AUTOPSY</h3>
                </div>
                <div className="flex gap-2">
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                        LIVE
                    </span>
                </div>
            </div>

            {/* Logs List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2 font-mono text-sm">
                {logs.length === 0 && (
                    <div className="text-center text-muted-foreground py-10 opacity-50">
                        Waiting for system telemetry...
                    </div>
                )}
                {logs.map((log, i) => (
                    <div key={i} className="flex gap-3 group hover:bg-muted/10 p-2 rounded transition-colors">
                        <span className="text-muted-foreground w-12 shrink-0 text-xs mt-0.5">
                            {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'now'}
                        </span>
                        <div className="flex-1">
                            <span className={`uppercase text-xs font-bold mr-2 ${log.role === 'RISK' ? 'text-orange-500' :
                                    log.role === 'EXECUTION' ? 'text-green-500' :
                                        log.role === 'ANALYST' ? 'text-blue-500' : 'text-purple-500'
                                }`}>
                                [{log.role}]
                            </span>
                            <span className="text-foreground/90">{log.content}</span>
                        </div>
                        {isTradeLog(log) && (
                            <button
                                onClick={() => setSelectedLog(log)}
                                className="opacity-0 group-hover:opacity-100 transition-opacity text-xs bg-primary/10 text-primary hover:bg-primary/20 px-2 py-1 rounded flex items-center gap-1"
                            >
                                <Search className="w-3 h-3" />
                                View Autopsy
                            </button>
                        )}
                    </div>
                ))}
            </div>

            {/* Autopsy Modal */}
            {selectedLog && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
                    <div className="bg-card w-full max-w-lg border border-border rounded-xl shadow-2xl p-6 relative m-4">
                        <button
                            onClick={() => setSelectedLog(null)}
                            className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
                        >
                            <X className="w-5 h-5" />
                        </button>

                        <div className="flex items-center gap-2 mb-6 text-destructive">
                            <AlertTriangle className="w-6 h-6" />
                            <h2 className="text-xl font-bold">Trade Autopsy</h2>
                        </div>

                        <div className="space-y-4">
                            <div className="p-4 bg-muted/30 rounded-lg border border-border">
                                <label className="text-xs text-muted-foreground uppercase font-bold block mb-1">Raw Log Content</label>
                                <code className="text-sm text-foreground font-mono block break-words">
                                    {selectedLog.content}
                                </code>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-3 bg-secondary/20 rounded border border-border">
                                    <label className="text-xs text-muted-foreground block">Agent</label>
                                    <span className="font-bold">{selectedLog.role}</span>
                                </div>
                                <div className="p-3 bg-secondary/20 rounded border border-border">
                                    <label className="text-xs text-muted-foreground block">Result</label>
                                    <span className="font-bold text-green-400">EXECUTED</span>
                                </div>
                            </div>

                            {/* Hypothetical Data Extraction */}
                            <div className="mt-4">
                                <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                                    <Search className="w-4 h-4" />
                                    Decision Context
                                </h4>
                                <ul className="text-sm space-y-2 text-muted-foreground list-disc pl-5">
                                    <li>Signal Confidence: <span className="text-foreground font-mono">High (0.92)</span></li>
                                    <li>Risk Veto: <span className="text-foreground font-mono">PASSED</span></li>
                                    <li>Market Regime: <span className="text-foreground font-mono">Gaussian</span></li>
                                    <li>Slippage Est: <span className="text-foreground font-mono">0.02%</span></li>
                                </ul>
                            </div>
                        </div>

                        <div className="mt-8 flex justify-end">
                            <button
                                onClick={() => setSelectedLog(null)}
                                className="btn-primary"
                            >
                                Close Report
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AutopsyPanel;
