import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { METRICS } from "./MetricToggles";

export default function MetricsChart({ lld, duration, currentTime, enabledMetrics }) {
  const data = useMemo(() => {
    if (!lld || !lld.F0 || lld.F0.length === 0) return [];
    const len = lld.F0.length;
    const step = duration / len;
    return Array.from({ length: len }, (_, i) => {
      const point = { t: +(i * step).toFixed(3) };
      for (const m of METRICS) {
        const val = lld[m.key]?.[i];
        point[m.key] = val === null ? undefined : val;
      }
      return point;
    });
  }, [lld, duration]);

  if (data.length === 0) return <div className="chart-empty">Нет данных</div>;

  const caretX = currentTime != null ? +currentTime.toFixed(3) : null;
  const activeMetrics = METRICS.filter((m) => enabledMetrics.includes(m.key));

  return (
    <div className="metrics-chart">
      {activeMetrics.map((m) => (
        <div key={m.key} className="chart-row">
          <span className="chart-label" style={{ color: m.color }}>{m.label}</span>
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={data} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="t" tick={{ fontSize: 10, fill: "#888" }} />
              <YAxis tick={{ fontSize: 10, fill: "#888" }} width={50} />
              <Tooltip
                contentStyle={{ background: "#1a1a2e", border: "1px solid #333", fontSize: 12 }}
                labelFormatter={(v) => `${v}s`}
              />
              <Line
                type="monotone"
                dataKey={m.key}
                stroke={m.color}
                dot={false}
                connectNulls={false}
                strokeWidth={1.5}
                isAnimationActive={false}
              />
              {caretX != null && (
                <ReferenceLine x={caretX} stroke="#ff006e" strokeWidth={2} />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      ))}
    </div>
  );
}
