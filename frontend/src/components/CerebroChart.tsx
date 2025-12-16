import React from 'react';
import {
    ComposedChart,
    Line,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ReferenceLine,
} from 'recharts';

interface DataPoint {
    time: string;
    price?: number;
    p10?: number;
    median?: number;
    p90?: number;
    isForecast?: boolean;
}

interface CerebroChartProps {
    data: DataPoint[];
}

const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        const price = payload.find((p: any) => p.dataKey === 'price');
        const median = payload.find((p: any) => p.dataKey === 'median');
        const p10 = payload.find((p: any) => p.dataKey === 'p10');
        const p90 = payload.find((p: any) => p.dataKey === 'p90');

        return (
            <div className="bg-slate-900 border border-slate-700 p-3 rounded shadow-xl text-xs font-mono">
                <p className="text-slate-400 mb-2">{label}</p>
                {price && (
                    <p className="text-emerald-400 font-bold">
                        Price: ${price.value.toFixed(2)}
                    </p>
                )}
                {median && (
                    <>
                        <p className="text-blue-400 font-bold mt-1">
                            Forecast: ${median.value.toFixed(2)}
                        </p>
                        {p10 && p90 && (
                            <p className="text-blue-500/80 text-[10px]">
                                Range: ${p10.value.toFixed(2)} - ${p90.value.toFixed(2)}
                            </p>
                        )}
                    </>
                )}
            </div>
        );
    }
    return null;
};

const CerebroChart: React.FC<CerebroChartProps> = ({ data }) => {
    // Find the index where forecast begins to place reference line
    const forecastStartIndex = data.findIndex((d) => d.isForecast);
    const nowLabel = forecastStartIndex !== -1 ? data[forecastStartIndex].time : '';

    return (
        <div className="w-full h-full min-h-[300px] bg-slate-900/30 rounded-lg p-2">
            <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                    data={data}
                    margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                    <defs>
                        <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                        </linearGradient>
                    </defs>

                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />

                    <XAxis
                        dataKey="time"
                        stroke="#64748b"
                        tick={{ fontSize: 10 }}
                        interval="preserveStartEnd"
                    />

                    <YAxis
                        domain={['auto', 'auto']}
                        stroke="#64748b"
                        tick={{ fontSize: 10 }}
                        tickFormatter={(value) => `$${value}`}
                        width={40}
                    />

                    <Tooltip content={<CustomTooltip />} />

                    {/* Reference Line for "Now" */}
                    {nowLabel && (
                        <ReferenceLine
                            x={nowLabel}
                            stroke="#94a3b8"
                            strokeDasharray="3 3"
                            label={{ position: 'top', value: 'NOW', fill: '#94a3b8', fontSize: 10 }}
                        />
                    )}

                    {/* Confidence Interval (Area) 
              We use 'p10' and 'p90' but Recharts Area usually takes one key.
              For a range area, we can stack or use range bar.
              However, standard trick for CI area in Recharts ComposedChart:
              Use 'p10' and 'p90' as separate areas or use a custom shape.
              Simpler approach for visualization: 
              Draw Area for p90 with white fill? No.
              Correct approach: Area chart usually requires [min, max] data format if using 'range'.
              Standard Recharts Area accepts `dataKey`.
              
              Hack for CI Area: 
              We can just simple render P10 and P90 lines invisible, and fill between?
              Recharts <Area> doesn't support 'fill between lines' easily out of box referencing other lines.
              
              Better approach for this specific request:
              Construct "range" data in the payload maybe?
              Actually, Recharts does data binding row by row.
              
              Let's iterate:
              Draw Area from 'p10' to 'p90'.
              Recharts Area 'dataKey' is single value (y-value).
              To do a range area (band), we typically use:
              <Area dataKey="p90" stroke="none" fill="..." baseLine="p10" /> (If Recharts supported baseLine dynamic) -> It doesn't fully yet for Area.
              
              Standard Workaround:
              Use two Areas?
              1. Area p90 (transparent or handled lower)
              
              Actually, `Area` has a `baseValue`. But that's static.
              
              Wait, Recharts 2.x supports `dataKey` as array `[min, max]` for Area? 
              Let's try dataKey as a function or array.
              Documentation says `dataKey`: The key of a group of data which should be unique in an area chart.
              
              Let's stick to the visual requirement: "Shaded Blue Area".
              Visual trick: 
              1. Stacked Area? No.
              2. <Area dataKey="range" /> where range is [p10, p90]. 
              Recharts `Area` accepts an array of [min, max] for the `dataKey` prop in some versions, or simply mapping.
              
              Actually, looking at Recharts `Area` props, it accepts `dataKey`.
              If `dataKey` returns an array `[min, max]`, it draws the area between.
              Let's verify this capability (common in Recharts for range charts).
              
              If not, we will just draw:
              Forecast Median (Line)
              Price (Line)
              
              Let's try defining a `ci` property in the data preparation or accessor.
              dataKey can be a function: (row) => [row.p10, row.p90]
          */}
                    <Area
                        type="monotone"
                        dataKey={(data) => [data.p10, data.p90]}
                        stroke="none"
                        fill="url(#colorForecast)"
                        connectNulls
                    />

                    {/* Forecast Median */}
                    <Line
                        type="monotone"
                        dataKey="median"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        strokeDasharray="5 5"
                        dot={false}
                        activeDot={{ r: 4 }}
                        connectNulls
                    />

                    {/* Historic Price */}
                    <Line
                        type="monotone"
                        dataKey="price"
                        stroke="#10b981"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4 }}
                        connectNulls
                    />

                </ComposedChart>
            </ResponsiveContainer>
        </div>
    );
};

export default CerebroChart;
