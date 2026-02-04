import React from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Signal } from '@/types/signals';

interface SignalCardProps {
    signal: Signal;
}

const SignalCard: React.FC<SignalCardProps> = ({ signal }) => {
    // Determine badge color based on risk level
    const getRiskColor = (risk: string) => {
        switch (risk?.toLowerCase()) {
            case 'baixo': return 'bg-green-500 hover:bg-green-600'; // Custom types often need explicit classes if not mapped to variants
            case 'médio': return 'bg-yellow-500 hover:bg-yellow-600';
            case 'alto': return 'destructive'; // Using shadcn variant name
            case 'crítico': return 'destructive';
            default: return 'secondary';
        }
    };

    const getSignalColor = (type: string) => {
        if (type.includes('BUY') || type.includes('LONG')) return 'text-green-400';
        if (type.includes('SELL') || type.includes('SHORT')) return 'text-red-400';
        return 'text-blue-400';
    }

    return (
        <Card className="w-full bg-slate-900 border-slate-800 text-slate-100 shadow-lg hover:shadow-xl transition-all duration-200">
            <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                    <div>
                        <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
                            {signal.option_symbol}
                            <span className="text-xs font-normal text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                                {signal.ticker}
                            </span>
                        </CardTitle>
                        <CardDescription className="text-slate-400 mt-1">
                            {signal.strategy}
                        </CardDescription>
                    </div>
                    <Badge variant={getRiskColor(signal.risk_level) as any} className="uppercase text-xs" >
                        {signal.risk_level} Risk
                    </Badge>
                </div>
            </CardHeader>
            <CardContent>
                <div className="space-y-3">
                    <div className="flex justify-between border-b border-slate-800 pb-2">
                        <span className="text-sm text-slate-500">Signal Type</span>
                        <span className={`font-bold ${getSignalColor(signal.signal_type)}`}>{signal.signal_type}</span>
                    </div>
                    <div className="flex justify-between border-b border-slate-800 pb-2">
                        <span className="text-sm text-slate-500">Spot Price</span>
                        <span className="font-mono">R$ {signal.spot_price.toFixed(2)}</span>
                    </div>
                    <div>
                        <span className="text-sm text-slate-500 block mb-1">Reasoning</span>
                        <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/50 p-2 rounded border border-slate-800">
                            {signal.reason}
                        </p>
                    </div>
                </div>
            </CardContent>
            <CardFooter className="bg-slate-950/30 pt-4">
                <div className="w-full">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Recommended Action</p>
                    <p className="text-sm font-medium text-blue-300">{signal.recommendation}</p>
                </div>
            </CardFooter>
        </Card>
    );
};

export default SignalCard;
