import React, { useState } from 'react';
import { Brain, ChevronDown, ChevronUp, Activity } from 'lucide-react';

interface ModelInvocation {
    timestamp: string;
    latency_ms: number;
    prediction: any;
    confidence: number | null;
}

interface ModelData {
    avg_latency_ms: number;
    invocations: ModelInvocation[];
    last_thought: string | null;
}

interface ModelsData {
    [modelName: string]: ModelData;
}

interface ModelMonitorProps {
    models: ModelsData;
}

export function ModelMonitor({ models }: ModelMonitorProps) {
    const [expandedModel, setExpandedModel] = useState<string | null>(null);

    const toggleExpand = (modelName: string) => {
        setExpandedModel(expandedModel === modelName ? null : modelName);
    };

    const modelIcons: Record<string, string> = {
        gemma2_9b: '🧠',
        finbert: '📊',
        chronos: '📈',
    };

    const modelLabels: Record<string, string> = {
        gemma2_9b: 'Gemma2 9B (LLM)',
        finbert: 'FinBERT (Sentiment)',
        chronos: 'Chronos-2 (Forecast)',
    };

    return (
        <div className="bg-card border border-border rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
                <Brain className="w-5 h-5 text-primary" />
                <h3 className="text-lg font-semibold">Model Performance</h3>
            </div>

            <div className="space-y-3">
                {Object.keys(models).length === 0 ? (
                    <div className="text-muted-foreground text-sm text-center py-4">
                        No model data available
                    </div>
                ) : (
                    Object.entries(models).map(([modelName, data]) => {
                        const isExpanded = expandedModel === modelName;
                        const latestInvocation = data.invocations[0];

                        return (
                            <div
                                key={modelName}
                                className="border border-border/50 rounded-md overflow-hidden"
                            >
                                {/* Header */}
                                <div
                                    className="p-4 hover:bg-accent/5 cursor-pointer transition-colors"
                                    onClick={() => toggleExpand(modelName)}
                                >
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <span className="text-lg">
                                                {modelIcons[modelName] || '🤖'}
                                            </span>
                                            <span className="font-medium">
                                                {modelLabels[modelName] || modelName}
                                            </span>
                                        </div>
                                        {isExpanded ? (
                                            <ChevronUp className="w-4 h-4 text-muted-foreground" />
                                        ) : (
                                            <ChevronDown className="w-4 h-4 text-muted-foreground" />
                                        )}
                                    </div>

                                    <div className="grid grid-cols-3 gap-4 mt-3 text-sm">
                                        <div>
                                            <div className="text-muted-foreground text-xs">
                                                Avg Latency
                                            </div>
                                            <div className="font-mono text-foreground">
                                                {data.avg_latency_ms.toFixed(1)}ms
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-muted-foreground text-xs">
                                                Invocations
                                            </div>
                                            <div className="font-mono text-foreground">
                                                {data.invocations.length}
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-muted-foreground text-xs">
                                                Last Confidence
                                            </div>
                                            <div className="font-mono text-foreground">
                                                {latestInvocation?.confidence != null
                                                    ? (latestInvocation.confidence * 100).toFixed(0) + '%'
                                                    : 'N/A'}
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Expanded Section - LLM Reasoning */}
                                {isExpanded && data.last_thought && (
                                    <div className="border-t border-border/50 p-4 bg-accent/5">
                                        <div className="flex items-center gap-2 mb-2">
                                            <Activity className="w-4 h-4 text-primary" />
                                            <span className="text-sm font-medium">Last Reasoning</span>
                                        </div>
                                        <div className="bg-background border border-border rounded p-3 text-xs font-mono whitespace-pre-wrap max-h-64 overflow-y-auto">
                                            {data.last_thought}
                                        </div>
                                    </div>
                                )}

                                {/* Expanded Section - Recent Invocations */}
                                {isExpanded && data.invocations.length > 0 && (
                                    <div className="border-t border-border/50 p-4 bg-accent/5">
                                        <div className="text-sm font-medium mb-2">
                                            Recent Invocations
                                        </div>
                                        <div className="space-y-2 max-h-48 overflow-y-auto">
                                            {data.invocations.slice(0, 5).map((inv, idx) => (
                                                <div
                                                    key={idx}
                                                    className="text-xs flex justify-between items-center border-l-2 border-primary/30 pl-2"
                                                >
                                                    <span className="text-muted-foreground font-mono">
                                                        {new Date(inv.timestamp).toLocaleTimeString()}
                                                    </span>
                                                    <div className="flex gap-3">
                                                        <span className="text-foreground">
                                                            {inv.latency_ms.toFixed(0)}ms
                                                        </span>
                                                        {inv.confidence != null && (
                                                            <span className="text-primary">
                                                                {(inv.confidence * 100).toFixed(0)}%
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
