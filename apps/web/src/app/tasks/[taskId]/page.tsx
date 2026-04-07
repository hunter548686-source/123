"use client";

import { useParams } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import { ConsoleShell } from "@/components/console-shell";
import { StageTrack } from "@/components/stage-track";
import { StatusBadge } from "@/components/status-badge";
import { cancelTask, fetchTaskDetail, requestArtifactDownload, retryTask } from "@/lib/api";

export default function TaskDetailPage() {
  const params = useParams<{ taskId: string }>();
  const [detail, setDetail] = useState<Awaited<ReturnType<typeof fetchTaskDetail>> | null>(null);
  const [downloadMessage, setDownloadMessage] = useState("");
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (!params?.taskId) return;
    void fetchTaskDetail(params.taskId).then(setDetail);
  }, [params?.taskId]);

  if (!detail) {
    return (
      <ConsoleShell current="/tasks" eyebrow="Task Detail" title="任务详情">
        <div className="glass-panel rounded-[1.75rem] p-8 text-white/62">加载中...</div>
      </ConsoleShell>
    );
  }

  const task = detail.task;

  return (
    <ConsoleShell
      current="/tasks"
      eyebrow="Task Detail"
      title={`任务 #${task.id}`}
      actions={
        <>
          <button
            type="button"
            onClick={() =>
              startTransition(async () => {
                await retryTask(String(task.id));
                const next = await fetchTaskDetail(String(task.id));
                setDetail(next);
              })
            }
            className="rounded-full border border-white/14 px-5 py-3 text-sm text-white/72 hover:bg-white/6"
          >
            {isPending ? "处理中..." : "手动重试"}
          </button>
          <button
            type="button"
            onClick={() =>
              startTransition(async () => {
                await cancelTask(String(task.id));
                const next = await fetchTaskDetail(String(task.id));
                setDetail(next);
              })
            }
            className="rounded-full border border-rose-400/25 px-5 py-3 text-sm text-rose-100 hover:bg-rose-400/10"
          >
            取消任务
          </button>
        </>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="space-y-6">
          <StageTrack
            planning={task.planningStatus}
            execution={task.executionStatus}
            review={task.reviewStatus}
            currentStage={task.workflowStage}
          />

          <section className="glass-panel rounded-[1.75rem] p-6">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-white/45">Template</p>
                <p className="mt-3 text-lg text-white">{task.templateId}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-white/45">Strategy</p>
                <p className="mt-3 text-lg uppercase text-white">{task.strategy}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-white/45">Provider</p>
                <p className="mt-3 text-lg text-white">{task.selectedProvider ?? "pending"}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-white/45">GPU</p>
                <p className="mt-3 text-lg text-white">{task.selectedGpuType ?? "pending"}</p>
              </div>
            </div>

            <div className="mt-6 h-3 overflow-hidden rounded-full bg-white/8">
              <div className="h-full rounded-full bg-cyan-300" style={{ width: `${task.progress}%` }} />
            </div>
            <div className="mt-3 flex items-center justify-between text-sm text-white/58">
              <span>任务进度</span>
              <span>{task.progress}%</span>
            </div>

            {task.planSummary ? (
              <div className="mt-6 rounded-[1.2rem] border border-white/8 bg-white/4 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-white/45">Plan Summary</p>
                <p className="mt-3 text-sm leading-7 text-white/68">{task.planSummary}</p>
              </div>
            ) : null}

            {task.executionBrief ? (
              <div className="mt-4 rounded-[1.2rem] border border-white/8 bg-white/4 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-white/45">Execution Brief</p>
                <p className="mt-3 text-sm leading-7 text-white/68">{task.executionBrief}</p>
              </div>
            ) : null}

            {task.codingInstructions ? (
              <div className="mt-4 rounded-[1.2rem] border border-cyan-200/15 bg-cyan-200/5 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-cyan-100/70">Coding Instructions</p>
                <p className="mt-3 text-sm leading-7 text-cyan-50/82">{task.codingInstructions}</p>
              </div>
            ) : null}

            {task.reviewSummary ? (
              <div className="mt-4 rounded-[1.2rem] border border-white/8 bg-white/4 p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-white/45">Review Summary</p>
                  <StatusBadge
                    label={
                      task.reviewApproved == null
                        ? `round ${task.reviewRound ?? 0}`
                        : task.reviewApproved
                          ? `approved / round ${task.reviewRound ?? 0}`
                          : `fixing / round ${task.reviewRound ?? 0}`
                    }
                    tone={
                      task.reviewApproved == null
                        ? "neutral"
                        : task.reviewApproved
                          ? "success"
                          : "warning"
                    }
                  />
                </div>
                <p className="mt-3 text-sm leading-7 text-white/68">{task.reviewSummary}</p>
              </div>
            ) : null}

            {task.latestFixInstructions ? (
              <div className="mt-4 rounded-[1.2rem] border border-amber-200/15 bg-amber-200/5 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-amber-100/70">Latest Fix Instructions</p>
                <p className="mt-3 text-sm leading-7 text-amber-50/85">{task.latestFixInstructions}</p>
              </div>
            ) : null}
          </section>

          <section className="glass-panel rounded-[1.75rem] p-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">运行历史</h3>
              <StatusBadge label={`${detail.runs.length} attempts`} tone="accent" />
            </div>
            <div className="mt-4 space-y-3">
              {detail.runs.map((run) => (
                <div key={run.id} className="rounded-[1.2rem] border border-white/8 bg-white/3 p-4">
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-white">
                      Attempt {run.attemptNo} / {run.provider}
                    </p>
                    <StatusBadge
                      label={run.status}
                      tone={run.status === "finished" ? "success" : run.status === "error" ? "danger" : "accent"}
                    />
                  </div>
                  <p className="mt-3 text-sm leading-7 text-white/58">
                    {run.gpuType} / {run.runtimeSeconds}s / 成本 {Number(run.providerCost).toFixed(2)}
                  </p>
                  {run.failReason ? <p className="mt-2 text-sm text-rose-100">{run.failReason}</p> : null}
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className="space-y-6">
          <section className="glass-panel rounded-[1.75rem] p-6">
            <h3 className="text-lg font-semibold text-white">返工审查链</h3>
            <div className="mt-4 space-y-3">
              {detail.codeEditChains?.length ? (
                detail.codeEditChains.map((chain) => (
                  <div key={chain.id} className="rounded-[1.15rem] border border-white/8 bg-white/3 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-white">
                        chain #{chain.id} / {chain.status}
                      </p>
                      <StatusBadge
                        label={
                          chain.finalReviewApproved == null
                            ? `round ${chain.currentReviewRound}`
                            : chain.finalReviewApproved
                              ? "approved"
                              : "failed"
                        }
                        tone={
                          chain.finalReviewApproved == null
                            ? "neutral"
                            : chain.finalReviewApproved
                              ? "success"
                              : "danger"
                        }
                      />
                    </div>
                    <p className="mt-3 text-xs text-white/56">
                      started {chain.startedReviewRound} / current {chain.currentReviewRound} / executions {chain.totalExecutions}
                    </p>
                    {chain.latestReviewSummary ? (
                      <p className="mt-3 text-sm leading-7 text-white/62">{chain.latestReviewSummary}</p>
                    ) : null}
                    {chain.latestFixInstructions ? (
                      <p className="mt-2 text-sm leading-7 text-amber-100/85">{chain.latestFixInstructions}</p>
                    ) : null}
                  </div>
                ))
              ) : (
                <div className="rounded-[1.15rem] border border-dashed border-white/12 bg-black/10 p-4 text-sm text-white/56">
                  暂无返工审查记录
                </div>
              )}
            </div>
          </section>

          <section className="glass-panel rounded-[1.75rem] p-6">
            <h3 className="text-lg font-semibold text-white">事件日志</h3>
            <div className="mt-4 space-y-3">
              {detail.events.map((event) => {
                const detailPayload = (event as { detailPayload?: Record<string, unknown> | null }).detailPayload;
                return (
                  <div key={event.id} className="rounded-[1.15rem] border border-white/8 bg-white/3 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-white">
                        {event.source} / {event.stage}
                      </p>
                      <StatusBadge
                        label={event.level}
                        tone={
                          event.level === "success"
                            ? "success"
                            : event.level === "error"
                              ? "danger"
                              : event.level === "warn"
                                ? "warning"
                                : "neutral"
                        }
                      />
                    </div>
                    <p className="mt-3 text-sm leading-7 text-white/62">{event.message}</p>
                    {detailPayload ? (
                      <pre className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 text-xs leading-6 text-cyan-50/80">
                        {JSON.stringify(detailPayload, null, 2)}
                      </pre>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </section>

          <section className="glass-panel rounded-[1.75rem] p-6">
            <h3 className="text-lg font-semibold text-white">结果归档</h3>
            <div className="mt-4 space-y-3">
              {detail.artifacts.map((artifact) => (
                <div key={artifact.id} className="rounded-[1.15rem] border border-white/8 bg-white/3 p-4">
                  <p className="font-medium text-white">{artifact.type}</p>
                  <p className="mt-2 text-sm text-white/56">{artifact.storagePath}</p>
                  {artifact.downloadUrl ? (
                    <p className="mt-2 text-xs text-cyan-100/80">download: {artifact.downloadUrl}</p>
                  ) : null}
                  <p className="mt-2 text-sm text-white/56">
                    {(artifact.fileSize / 1_000_000).toFixed(1)} MB / {new Date(artifact.createdAt).toLocaleString()}
                  </p>
                  <div className="mt-3 flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() =>
                        startTransition(async () => {
                          try {
                            const res = await requestArtifactDownload(task.id, artifact.id);
                            window.open(res.download_url, "_blank", "noopener,noreferrer");
                            setDownloadMessage(`artifact #${artifact.id} download opened`);
                          } catch (error) {
                            setDownloadMessage(error instanceof Error ? error.message : "download failed");
                          }
                        })
                      }
                      className="rounded-full border border-cyan-300/35 px-4 py-2 text-xs text-cyan-100 hover:bg-cyan-300/10"
                    >
                      下载
                    </button>
                    {artifact.checksum ? (
                      <span className="text-xs text-white/52">checksum: {artifact.checksum}</span>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
            {downloadMessage ? (
              <p className="mt-4 text-xs text-cyan-100/80">{downloadMessage}</p>
            ) : null}
          </section>
        </div>
      </div>
    </ConsoleShell>
  );
}
