"use client"

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface EquityChartProps {
    data: number[];
}

export default function EquityChart({ data }: EquityChartProps) {
    // Transform array [10000, 10100, ...] into object array for Recharts
    const chartData = data.map((value, index) => ({
        day: index,
        equity: value
    }));

    // Calculate dynamic Y domain (min/max with buffer)
    const minValue = Math.min(...data);
    const maxValue = Math.max(...data);
    const padding = (maxValue - minValue) * 0.1;

    return (
        <Card className="bg-slate-900 border-slate-800 col-span-2">
            <CardHeader>
                <CardTitle className="text-slate-100">Equity Curve</CardTitle>
            </CardHeader>
            <CardContent className="pl-0">
                <div className="h-[300px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                            <XAxis
                                dataKey="day"
                                stroke="#94a3b8"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                                tickFormatter={(val) => `D${val}`}
                            />
                            <YAxis
                                stroke="#94a3b8"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                                tickFormatter={(val) => `R$${val / 1000}k`}
                                domain={[minValue - padding, maxValue + padding]}
                            />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f1f5f9' }}
                                itemStyle={{ color: '#10b981' }}
                                formatter={(value: number | undefined) => [`R$ ${value?.toFixed(2) ?? "0.00"}`, "Equity"]}
                                labelFormatter={(label) => `Day ${label}`}
                            />
                            <Line
                                type="monotone"
                                dataKey="equity"
                                stroke="#10b981"
                                strokeWidth={2}
                                dot={false}
                                activeDot={{ r: 6, fill: "#10b981" }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    )
}
