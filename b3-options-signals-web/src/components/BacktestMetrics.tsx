import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Percent, Activity, DollarSign, BarChart3 } from "lucide-react";

interface BacktestMetricsProps {
    metrics: {
        total_trades: number;
        win_rate: number;
        total_return_pct: number;
        total_profit: number;
        max_drawdown: number;
        profit_factor: number;
    };
}

export default function BacktestMetrics({ metrics }: BacktestMetricsProps) {
    const isProfit = metrics.total_return_pct >= 0;

    return (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            <Card className="bg-slate-900 border-slate-800">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-slate-400">Total Return</CardTitle>
                    {isProfit ? <TrendingUp className="h-4 w-4 text-emerald-500" /> : <TrendingDown className="h-4 w-4 text-rose-500" />}
                </CardHeader>
                <CardContent>
                    <div className={`text-2xl font-bold ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {metrics.total_return_pct}%
                    </div>
                    <p className="text-xs text-slate-500">
                        Total PnL: <span className="font-mono">R$ {metrics.total_profit.toFixed(2)}</span>
                    </p>
                </CardContent>
            </Card>

            <Card className="bg-slate-900 border-slate-800">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-slate-400">Win Rate</CardTitle>
                    <Percent className="h-4 w-4 text-blue-500" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold text-slate-100">{metrics.win_rate}%</div>
                    <p className="text-xs text-slate-500">
                        {metrics.total_trades} trades executed
                    </p>
                </CardContent>
            </Card>

            <Card className="bg-slate-900 border-slate-800">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-slate-400">Profit Factor</CardTitle>
                    <BarChart3 className="h-4 w-4 text-purple-500" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold text-slate-100">{metrics.profit_factor}</div>
                    <p className="text-xs text-slate-500">
                        Ratio of Gross Profit / Gross Loss
                    </p>
                </CardContent>
            </Card>
        </div>
    );
}
