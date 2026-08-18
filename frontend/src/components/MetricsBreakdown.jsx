const COLORS = {
  high: "#4caf50",
  mid: "#ff9800",
  low: "#f44336",
};

function barColor(score) {
  if (score > 70) return COLORS.high;
  if (score >= 40) return COLORS.mid;
  return COLORS.low;
}

export default function MetricsBreakdown({ subscores }) {
  if (!subscores || subscores.length === 0) return null;

  return (
    <div className="metrics-breakdown">
      {subscores.map((s) => (
        <div key={s.name} className="metric-row">
          <span className="metric-name">{s.name}</span>
          <div className="metric-bar-bg">
            <div
              className="metric-bar-fill"
              style={{ width: `${s.score}%`, backgroundColor: barColor(s.score) }}
            />
          </div>
          <span className="metric-score">{s.score}</span>
        </div>
      ))}
    </div>
  );
}
