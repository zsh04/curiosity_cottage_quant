import React from 'react';
import { Activity, Zap, Shield, TrendingUp } from 'lucide-react';

interface AgentMetric {
    timestamp: string;
    latency_ms: number;
    success: boolean;
    output: any;
    error?: string;
}

interface AgentData {
    [agentName: string]: AgentMetric[];
}

interface AgentMonitorProps {
    agents: AgentData;
}

export function AgentMonitor({ agents }: AgentMonitorProps) {
    // Calculate stats for each agent
    const getAgentStats = (metrics: AgentMetric[]) => {
        if (!metrics || metrics.length === 0) {
            return { avgLatency: 0, successRate: 0, lastRun: null };
        }

        const avgLatency =
            metrics.reduce((sum, m) => sum + m.latency_ms, 0) / metrics.length;
        const successCount = metrics.filter((m) => m.success).length;
        const successRate = (successCount / metrics.length) * 100;
        const lastRun = metrics[0]?.timestamp;

        return { avgLatency, successRate, lastRun };
    };

    const agentIcons: Record<string, React.ReactNode> = {
        analyst: <Activity className="w-5 h-5" />,
        risk: <Shield className="w-5 h-5" />,
        execution: <Zap className="w-5 h-5" />,
    };

    const agentNames: Record<string, string> = {
        analyst: 'Analyst',
        risk: 'Risk Guardian',
        execution: 'Execution',
    };

    return (
        <div className="bg-card border border-border rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="w-5 h-5 text-primary" />
                <h3 className="text-lg font-semibold">Agent Performance</h3>
            </div>

            <div className="space-y-4">
                {Object.keys(agents).length === 0 ? (
                    <div className="text-muted-foreground text-sm text-center py-4">
                        No agent data available
                    </div>
                ) : (
                    Object.entries(agents).map(([agentName, metrics]) => {
                        const stats = getAgentStats(metrics);

                        return (
                            <div
                                key={agentName}
                                className="border border-border/50 rounded-md p-4 hover:bg-accent/5 transition-colors"
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                        <div className="text-primary">
                                            {agentIcons[agentName] || <Activity className="w-5 h-5" />}
                                        </div>
                                        <span className="font-medium">
                                            {agentNames[agentName] || agentName}
                                        </span>
                                    </div>
                                    <div
                                        className={`text-xs px-2 py-1 rounded ${stats.successRate >= 90
                                                ? 'bg-green-500/10 text-green-500'
                                                : stats.successRate >= 70
                                                    ? 'bg-yellow-500/10 text-yellow-500'
                                                    : 'bg-red-500/10 text-red-500'
                                            }`}
                                    >
                                        {stats.successRate.toFixed(0)}% Success
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4 text-sm">
                                    <div>
                                        <div className="text-muted-foreground text-xs">Avg Latency</div>
                                        <div className="font-mono text-foreground">
                                            {stats.avgLatency.toFixed(1)}ms
                                        </div>
                                    </div>
                                    <div>
                                        <div className="text-muted-foreground text-xs">Last Run</div>
                                        <div className="font-mono text-foreground text-xs">
                                            {stats.lastRun
                                                ? new Date(stats.lastRun).toLocaleTimeString()
                                                : 'N/A'}
                                        </div>
                                    </div>
                                </div>

                                {/* Recent failures */}
                                {metrics.some((m) => !m.success) && (
                                    <div className="mt-2 text-xs text-red-500">
                                        ⚠️ {metrics.filter((m) => !m.success).length} recent failures
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
