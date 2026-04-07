type StatusBadgeProps = {
  label: string;
  tone?: "neutral" | "success" | "warning" | "danger" | "accent";
};

const toneClassMap = {
  neutral: "border-white/12 text-white/76 bg-white/6",
  success: "border-emerald-400/30 text-emerald-200 bg-emerald-400/10",
  warning: "border-amber-300/30 text-amber-100 bg-amber-400/10",
  danger: "border-rose-400/30 text-rose-100 bg-rose-400/10",
  accent: "border-cyan-300/30 text-cyan-100 bg-cyan-400/10",
};

export function StatusBadge({ label, tone = "neutral" }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-medium uppercase tracking-[0.2em] ${toneClassMap[tone]}`}
    >
      {label}
    </span>
  );
}
