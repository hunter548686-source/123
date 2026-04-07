"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { ConsoleShell } from "@/components/console-shell";
import { StatusBadge } from "@/components/status-badge";
import { createTask, fetchQuote } from "@/lib/api";

export default function NewTaskPage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("一支带电影感的城市夜景广告片，镜头平稳推进。");
  const [strategy, setStrategy] = useState("stable");
  const [resolution, setResolution] = useState("1080p");
  const [durationSeconds, setDurationSeconds] = useState(8);
  const [quote, setQuote] = useState<{
    estimated_price: number;
    estimated_runtime_minutes: number;
    risk_note: string;
    recommended_offer: { provider: string; gpuType?: string; gpu_type?: string };
  } | null>(null);
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    void fetchQuote({
      task_type: "text_to_video",
      strategy,
      duration_seconds: durationSeconds,
      resolution,
      output_count: 1,
      execution_mode: "hybrid",
    }).then(setQuote);
  }, [durationSeconds, resolution, strategy]);

  const providerLabel = useMemo(() => {
    if (!quote) return "--";
    return `${quote.recommended_offer.provider} / ${
      quote.recommended_offer.gpuType ?? quote.recommended_offer.gpu_type ?? "RTX 4090"
    }`;
  }, [quote]);

  return (
    <ConsoleShell current="/tasks/new" eyebrow="Create Flow" title="新建任务">
      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <section className="glass-panel rounded-[1.75rem] p-6">
          <div className="grid gap-5 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm text-white/72">任务类型</label>
              <div className="w-full rounded-[1rem] border border-white/12 bg-white/4 px-4 py-3 text-white">
                text_to_video
              </div>
            </div>
            <div>
              <label className="mb-2 block text-sm text-white/72">模板</label>
              <div className="w-full rounded-[1rem] border border-white/12 bg-white/4 px-4 py-3 text-white">
                wanx-v1
              </div>
            </div>
            <div>
              <label className="mb-2 block text-sm text-white/72">策略</label>
              <select
                value={strategy}
                onChange={(event) => setStrategy(event.target.value)}
                className="w-full rounded-[1rem] border border-white/12 bg-white/4 px-4 py-3 text-white outline-none"
              >
                <option value="cheap">cheap</option>
                <option value="stable">stable</option>
                <option value="urgent">urgent</option>
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm text-white/72">分辨率</label>
              <select
                value={resolution}
                onChange={(event) => setResolution(event.target.value)}
                className="w-full rounded-[1rem] border border-white/12 bg-white/4 px-4 py-3 text-white outline-none"
              >
                <option value="720p">720p</option>
                <option value="1080p">1080p</option>
                <option value="4k">4k</option>
              </select>
            </div>
          </div>

          <div className="mt-5">
            <label className="mb-2 block text-sm text-white/72">Prompt</label>
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              rows={8}
              className="w-full rounded-[1.2rem] border border-white/12 bg-white/4 px-4 py-3 text-white outline-none"
            />
          </div>

          <div className="mt-5">
            <label className="mb-2 block text-sm text-white/72">视频时长（秒）</label>
            <input
              type="range"
              min={4}
              max={16}
              step={2}
              value={durationSeconds}
              onChange={(event) => setDurationSeconds(Number(event.target.value))}
              className="w-full"
            />
            <p className="mt-2 text-sm text-white/56">{durationSeconds}s</p>
          </div>

          {error ? (
            <div className="mt-5 rounded-[1rem] border border-rose-400/25 bg-rose-400/10 px-4 py-3 text-sm text-rose-100">
              {error}
            </div>
          ) : null}

          <button
            type="button"
            disabled={isPending || !quote}
            onClick={() =>
              startTransition(async () => {
                try {
                  const task = await createTask({
                    project_id: 1,
                    task_type: "text_to_video",
                    template_id: "wanx-v1",
                    strategy,
                    execution_mode: "hybrid",
                    input_payload: {
                      prompt,
                      duration_seconds: durationSeconds,
                      resolution,
                      retry_limit: 2,
                    },
                    quote_snapshot: {
                      estimated_price: quote?.estimated_price,
                      estimated_runtime_minutes: quote?.estimated_runtime_minutes,
                      recommended_offer: quote?.recommended_offer,
                    },
                  });
                  router.push(`/tasks/${task.id}`);
                } catch (createError) {
                  setError(
                    createError instanceof Error
                      ? createError.message
                      : "创建失败，请先登录并确认 API 已启动。",
                  );
                }
              })
            }
            className="display-font mt-8 rounded-full bg-white px-6 py-3 text-sm font-semibold text-slate-950 disabled:opacity-70"
          >
            {isPending ? "创建中..." : "立即创建任务"}
          </button>
        </section>

        <aside className="space-y-6">
          <section className="glass-panel rounded-[1.75rem] p-6">
            <p className="text-xs uppercase tracking-[0.24em] text-white/45">Quote</p>
            <h3 className="mt-3 text-2xl font-semibold text-white">实时报价面板</h3>
            <div className="mt-6 space-y-3 text-sm text-white/72">
              <div className="flex items-center justify-between">
                <span>推荐执行路径</span>
                <StatusBadge label={providerLabel} tone="accent" />
              </div>
              <div className="flex items-center justify-between">
                <span>预估耗时</span>
                <span>{quote?.estimated_runtime_minutes ?? "--"} 分钟</span>
              </div>
              <div className="flex items-center justify-between">
                <span>预估价格</span>
                <span>{quote?.estimated_price?.toFixed(2) ?? "--"} CNY</span>
              </div>
            </div>
            <p className="mt-5 text-sm leading-7 text-white/58">{quote?.risk_note ?? "等待报价..."}</p>
          </section>

          <section className="glass-panel rounded-[1.75rem] p-6">
            <p className="text-xs uppercase tracking-[0.24em] text-white/45">Execution Policy</p>
            <ul className="mt-4 space-y-3 text-sm leading-7 text-white/64">
              <li>默认执行模式为 hybrid：先本地整理执行摘要，再走云端 provider。</li>
              <li>cheap 策略会优先低价供给，失败时自动迁移。</li>
              <li>stable / urgent 会提高稳定性和启动速度权重。</li>
            </ul>
          </section>
        </aside>
      </div>
    </ConsoleShell>
  );
}
