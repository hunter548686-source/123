import { StatusBadge } from "./status-badge";

const toneByStatus = {
  completed: "success",
  in_progress: "accent",
  failed: "danger",
  pending: "neutral",
  skipped: "warning",
} as const;

type StageTrackProps = {
  planning: string;
  execution: string;
  review: string;
  currentStage: string;
};

export function StageTrack({ planning, execution, review, currentStage }: StageTrackProps) {
  const stages = [
    { key: "planning", label: "规划", value: planning },
    { key: "execution", label: "执行", value: execution },
    { key: "review", label: "审查", value: review },
  ];

  return (
    <div className="glass-panel rounded-[1.75rem] p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-cyan-100/70">Pipeline</p>
          <h3 className="display-font mt-2 text-xl font-semibold text-white">规划 / 执行 / 审查</h3>
        </div>
        <StatusBadge label={`当前阶段 ${currentStage}`} tone="accent" />
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {stages.map((stage) => (
          <div
            key={stage.key}
            className="rounded-[1.25rem] border border-white/8 bg-white/3 px-4 py-4"
          >
            <p className="text-sm text-white/90">{stage.label}</p>
            <div className="mt-3 flex items-center justify-between">
              <span className="text-xs uppercase tracking-[0.2em] text-white/45">
                {stage.value}
              </span>
              <StatusBadge
                label={stage.value.replace("_", " ")}
                tone={toneByStatus[(stage.value as keyof typeof toneByStatus) ?? "pending"] ?? "neutral"}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
