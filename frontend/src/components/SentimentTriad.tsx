import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { BrainCircuit } from 'lucide-react';

interface SentimentProps {
    label: string;
    score: number;
    // For the pie chart, we interpret score (usually -1 to 1 or 0 to 1) into prob buckets?
    // Or does FinBERT return probabilities for [Positive, Negative, Neutral]?
    // The prompt says "A Pie Chart showing Probabilities: [Bullish (Green), Neutral (Gray), Bearish (Red)]".
    // Since our BFF mock currently returns { label: '...', score: float }, we might need to fake the distribution 
    // or assume the score IS the probability of the label.
    // Let's sim the distribution based on the dominant label/score for visual flare if raw probs are missing.
    probs?: {
        bullish: number;
        neutral: number;
        bearish: number;
    }
}

const SentimentTriad: React.FC<SentimentProps> = ({ label = 'Neutral', score = 0.5, probs }) => {

    // If probs not provided, simulate based on label/score
    let data = [];
    if (probs) {
        data = [
            { name: 'Bullish', value: probs.bullish, color: '#10b981' }, // emerald-500
            { name: 'Neutral', value: probs.neutral, color: '#64748b' }, // slate-500
            { name: 'Bearish', value: probs.bearish, color: '#ef4444' }, // red-500
        ];
    } else {
        // Fallback simulation
        const high = score;
        const low = (1 - score) / 2;

        if (label.toLowerCase() === 'positive') {
            data = [
                { name: 'Bullish', value: high, color: '#10b981' },
                { name: 'Neutral', value: low, color: '#64748b' },
                { name: 'Bearish', value: low, color: '#ef4444' },
            ];
        } else if (label.toLowerCase() === 'negative') {
            data = [
                { name: 'Bullish', value: low, color: '#10b981' },
                { name: 'Neutral', value: low, color: '#64748b' },
                { name: 'Bearish', value: high, color: '#ef4444' },
            ];
        } else {
            data = [
                { name: 'Bullish', value: low, color: '#10b981' },
                { name: 'Neutral', value: high, color: '#64748b' },
                { name: 'Bearish', value: low, color: '#ef4444' },
            ];
        }
    }

    return (
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow h-full flex flex-col relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10">
                <BrainCircuit className="w-24 h-24 text-primary" />
            </div>

            <h2 className="text-lg font-semibold mb-2 flex items-center gap-2 z-10">
                <BrainCircuit className="w-5 h-5 text-primary" />
                Sentiment Triad
            </h2>

            <div className="flex-1 flex flex-col justify-center items-center relative min-h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie
                            data={data}
                            innerRadius={60}
                            outerRadius={80}
                            paddingAngle={5}
                            dataKey="value"
                            stroke="none"
                        >
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                        </Pie>
                        <Tooltip
                            contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }}
                            itemStyle={{ color: 'hsl(var(--foreground))' }}
                        />
                    </PieChart>
                </ResponsiveContainer>

                {/* Center Text */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-xs text-muted-foreground font-mono uppercase tracking-widest">DOMINANT</span>
                    <span className={`text-xl font-bold uppercase tracking-wider ${label.toLowerCase() === 'positive' ? 'text-green-500' :
                        label.toLowerCase() === 'negative' ? 'text-red-500' : 'text-slate-500'
                        }`}>
                        {label}
                    </span>
                    <span className="text-xs text-muted-foreground mt-1">{(score * 100).toFixed(1)}%</span>
                </div>
            </div>

            <div className="grid grid-cols-3 gap-2 mt-4">
                {data.map((d) => (
                    <div key={d.name} className="flex flex-col items-center text-center">
                        <div className="w-2 h-2 rounded-full mb-1" style={{ backgroundColor: d.color }} />
                        <span className="text-xs text-muted-foreground">{d.name}</span>
                        <span className="text-xs font-bold">{(d.value * 100).toFixed(0)}%</span>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default SentimentTriad;
