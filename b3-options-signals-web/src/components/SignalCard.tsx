import React from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Signal } from '@/types/signals';
import RiskBadge from './RiskBadge';
import { Copy } from 'lucide-react';

interface SignalCardProps {
    signal: Signal;
}

const SignalCard: React.FC<SignalCardProps> = ({ signal }) => {

    // Determine confidence color
    const getConfidenceColor = (score: number) => {
        if (score >= 80) return 'text-emerald-400';
        if (score >= 60) return 'text-yellow-400';
        return 'text-slate-400';
    };

    const getSignalColor = (type: string) => {
        if (type.includes('BUY') || type.includes('LONG')) return 'text-green-400';
        if (type.includes('SELL') || type.includes('SHORT')) return 'text-red-400';
        return 'text-blue-400';
    }

    const handleCopy = () => {
        const text = `🚨 SINAL B3\n\n🎯 ${signal.strategy}\n📊 ${signal.ticker} @ R$ ${signal.spot_price.toFixed(2)}\n🏷️ ${signal.signal_type}\n📦 Opção: ${signal.option_symbol || signal.ticker}\n\n💡 Motivo: ${signal.reason}`;
        navigator.clipboard.writeText(text);
    };

    return (
        <Card className="w-full bg-slate-900 border-slate-800 text-slate-100 shadow-lg hover:shadow-xl transition-all duration-200 hover:border-slate-700 group relative">
            <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                    <div>
                        <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
                            {signal.option_symbol || signal.ticker}
                            <span className="text-xs font-normal text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                                {signal.ticker}
                            </span>
                        </CardTitle>
                        <CardDescription className="text-slate-400 mt-1 font-medium group-hover:text-blue-300 transition-colors">
                            {signal.strategy}
                        </CardDescription>
                    </div>
                    {signal.risk_level && (
                        <div className="flex flex-col items-end gap-1">
                            <RiskBadge level={signal.risk_level} />
                            {signal.confidence_score !== undefined && (
                                <span className={`text-[10px] font-bold ${getConfidenceColor(signal.confidence_score)}`}>
                                    SCORE: {signal.confidence_score}/100
                                </span>
                            )}
                        </div>
                    )}
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
                        <span className="font-mono text-slate-200">R$ {signal.spot_price.toFixed(2)}</span>
                    </div>

                    {signal.technicals && (
                        <div className="flex justify-between border-b border-slate-800 pb-2 text-xs">
                            <span className="text-slate-500">Technicals</span>
                            <div className="flex gap-2">
                                <span>RSI: <span className={signal.technicals.rsi < 30 ? 'text-green-400' : signal.technicals.rsi > 70 ? 'text-red-400' : 'text-slate-300'}>{signal.technicals.rsi?.toFixed(0)}</span></span>
                                <span>IV: <span className="text-purple-400">{signal.technicals.iv?.toFixed(2)}</span></span>
                            </div>
                        </div>
                    )}

                    {signal.risk_flags && signal.risk_flags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                            {signal.risk_flags.map((flag, idx) => (
                                <span key={idx} className="text-[10px] bg-red-900/30 text-red-300 px-1.5 py-0.5 rounded border border-red-900/50">
                                    {flag}
                                </span>
                            ))}
                        </div>
                    )}

                    <div>
                        <span className="text-sm text-slate-500 block mb-1">Reasoning</span>
                        <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/50 p-2 rounded border border-slate-800">
                            {signal.reason}
                        </p>
                    </div>
                </div>
            </CardContent>
            <CardFooter className="bg-slate-950/30 pt-4 rounded-b-lg flex justify-between items-center">
                <div className="w-full">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Recommended Action</p>
                    <p className="text-sm font-medium text-blue-300">{signal.recommendation}</p>
                </div>
                <Button variant="ghost" size="icon" onClick={handleCopy} className="h-8 w-8 text-slate-500 hover:text-white" title="Copiar Estrutura">
                    <Copy className="h-4 w-4" />
                </Button>
            </CardFooter>
        </Card>
    );
};

export default SignalCard;
