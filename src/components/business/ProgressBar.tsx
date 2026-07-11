type ProgressBarProps = {
  label: string;
  value: number;
  max: number;
  suffix?: string;
};

export function ProgressBar({ label, value, max, suffix = "" }: ProgressBarProps) {
  const percent = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;

  return (
    <div className="progress-block">
      <div className="progress-label">
        <span>{label}</span>
        <strong>
          {value}
          {suffix} / {max}
          {suffix}
        </strong>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
