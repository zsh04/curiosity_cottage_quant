import React from 'react';
import { Activity, Radio, ShieldAlert } from 'lucide-react';

interface HeaderProps {
    symbol: string;
    price: number;
    regime: string;
    status: string;
    wsStatus: string;
}

const Header: React.FC<HeaderProps> = ({ symbol, price, regime, status, wsStatus }) => {
    const isActive = status === 'Active' || status === 'ACTIVE';
    const isVetoed = status === 'Vetoed' || status === 'VETOED'; // Adjust based on exact enum string

    // Determine color based on status
    const statusColor = isActive ? 'bg-green-500/20 text-green-400 border-green-500/50' :
        (isVetoed ? 'bg-red-500/20 text-red-400 border-red-500/50' : 'bg-yellow-500/20 text-yellow-400');

    return (
        <header className="p-6 border-b border-border bg-card/50 backdrop-blur-md sticky top-0 z-50">
            <div className="max-w-7xl mx-auto flex items-center justify-between">

                {/* Left: Brand & Symbol */}
                <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2">
                        <Activity className="w-6 h-6 text-primary" />
                        <h1 className="text-xl font-bold tracking-tight text-foreground">Curiosity Cottage <span className="text-muted-foreground font-normal">Terminal</span></h1>
                    </div>

                    <div className="h-8 w-px bg-border mx-2" />

                    <div className="flex items-center gap-4">
                        <div className="flex flex-col">
                            <span className="text-xs text-muted-foreground font-mono">SYMBOL</span>
                            <span className="text-2xl font-bold text-foreground font-mono">{symbol}</span>
                        </div>
                        <div className="flex flex-col">
                            <span className="text-xs text-muted-foreground font-mono">LIVE PRICE</span>
                            <span className="text-2xl font-bold text-accent font-mono animate-pulse">
                                ${price.toFixed(2)}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Right: Regime & Status */}
                <div className="flex items-center gap-4">

                    <div className="flex flex-col items-end mr-4">
                        <span className="text-xs text-muted-foreground font-mono uppercase">Market Regime</span>
                        <span className="text-sm font-semibold text-foreground border border-border px-2 py-1 rounded bg-secondary/50">
                            {regime}
                        </span>
                    </div>

                    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${statusColor}`}>
                        {isActive ? <Radio className="w-4 h-4 animate-ping" /> : <ShieldAlert className="w-4 h-4" />}
                        <span className="text-sm font-semibold tracking-wide uppercase">{status}</span>
                    </div>

                    <div className="flex items-center ml-4 text-xs text-muted-foreground">
                        <div className={`w-2 h-2 rounded-full mr-2 ${wsStatus === 'CONNECTED' ? 'bg-green-500' : 'bg-red-500'}`} />
                        {wsStatus}
                    </div>
                </div>
            </div>
        </header>
    );
};

export default Header;
