const METRICS = [
  { key: "F0", label: "F0 (высота голоса)", color: "#8ecae6" },
  { key: "Loudness", label: "Loudness (громкость)", color: "#ffb703" },
  { key: "Jitter", label: "Jitter (дрожание)", color: "#fb8500" },
];

export default function MetricToggles({ enabled, onToggle }) {
  return (
    <div className="metric-toggles">
      {METRICS.map((m) => (
        <label key={m.key} className="toggle-label">
          <input
            type="checkbox"
            checked={enabled.includes(m.key)}
            onChange={() => onToggle(m.key)}
          />
          <span style={{ color: m.color }}>{m.label}</span>
        </label>
      ))}
    </div>
  );
}

export { METRICS };
