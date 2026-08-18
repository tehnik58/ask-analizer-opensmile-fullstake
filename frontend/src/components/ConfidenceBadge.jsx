const COLORS = {
  Уверенно: "#4caf50",
  Средне: "#ff9800",
  Неуверенно: "#f44336",
};

export default function ConfidenceBadge({ score, label }) {
  const color = COLORS[label] || "#888";
  return (
    <span
      className="confidence-badge"
      style={{ backgroundColor: color, color: "#fff", padding: "4px 12px", borderRadius: 12, fontWeight: 600 }}
    >
      {label} ({score}%)
    </span>
  );
}
