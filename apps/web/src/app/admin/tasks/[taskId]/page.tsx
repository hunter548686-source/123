"use client";

import { useParams } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import { ConsoleShell } from "@/components/console-shell";
import { StatusBadge } from "@/components/status-badge";
import {
  cancelAdminTask,
  fetchAdminTaskDetail,
  requestArtifactDownload,
  retryAdminTask,
} from "@/lib/api";

export default function AdminTaskDetailPage() {
  const params = useParams<{ taskId: string }>();
  const [detail, setDetail] = useState<Awaited<ReturnType<typeof fetchAdminTaskDetail>> | null>(null);
  const [message, setMessage] = useState("可在此查看任务运行细节与交付产物。");
  const [loadError, setLoadError] = useState("");
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (!params?.taskId) return;
    void fetchAdminTaskDetail(params.taskId)
      .then(setDetail)
      .catch((error) => {
        setLoadError(
          error instanceof Error ? error.message : "加载后台任务详情失败，请检查管理员权限。",
        );
      });
  }, [params?.taskId]);

  if (!detail) {
    return (
      <ConsoleShell current="/admin/tasks" eyebrow="Task Detail" title="任务详情">
        <div className="glass-panel rounded-[1.75rem] p-8 text-white/62">
          {loadError || "加载中..."}
        </div>
      </ConsoleShell>
    );
  }

  const task = detail.task;

  const refresh = async () => {
    const next = await fetchAdminTaskDetail(String(task.id));
    setDetail(next);
  };

  return (
    <ConsoleShell
      current="/admin/tasks"
      eyebrow="Ops Task Detail"
      title={`后台任务 #${task.id}`}
      actions={
        <>
          <button
            type="button"
            disabled={isPending}
            onClick={() =>
              startTransition(async () => {
                try {
                  await retryAdminTask(String(task.id));
                  await refresh();
                  setMessage(`任务 #${task.id} 已触发重试。`);
                } catch (error) {
                  setMessage(error instanceof Error ? error.message : "重试失败。");
                }
              })
            }
            className="rounded-full border border-white/14 px-5 py-3 text-sm text-white/72 hover:bg-white/6 disabled:opacity-60"
          >
            手动重试
          </button>
          <button
            type="button"
            disabled={isPending}
            onClick={() =>
              startTransition(async () => {
                try {
                  await cancelAdminTask(String(task.id));
                  await refresh();
                  setMessage(`任务 #${task.id} 已触发取消。`);
                } catch (error) {
                  setMessage(error instanceof Error ? error.message : "取消失败。");
                }
              })
            }
            className="rounded-full border border-rose-400/20 px-5 py-3 text-sm text-rose-100 hover:bg-rose-400/10 disabled:opacity-60"
          >
            取消任务
          </button>
        </>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[1.06fr_0.94fr]">
        <section className="space-y-6">
          <div className="glass-panel rounded-[1.75rem] p-6">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-white/45">状态</p>
                <p className="mt-3">
                  <StatusBadge label={`${task.workflowStage} / ${task.status}`} tone="accent" />
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-white/45">审查结论</p>
                <p className="mt-3">
                  <StatusBadge
                    label={
                      task.reviewApproved == null
                        ? `round ${task.reviewRound ?? 0}`
                        : task.reviewApproved
                          ? `approved · round ${task.reviewRound ?? 0}`
                          : `fixing · round ${task.reviewRound ?? 0}`
                    }
                    tone={
                      task.reviewApproved == null
                        ? "neutral"
                        : task.reviewApproved
                          ? "success"
                          : "warning"
                    }
                  />
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-white/45">Provider / GPU</p>
                <p className="mt-3 text-sm text-white/72">
                  {task.selectedProvider ?? "pending"} / {task.selectedGpuType ?? "pending"}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-white/45">报价 / 实扣 / 成本</p>
                <p className="mt-3 text-sm text-white/72">
                  {(task.quotedPrice ?? 0).toFixed(2)} / {(task.finalCharge ?? 0).toFixed(2)} / {(task.finalCost ?? 0).toFixed(2)}
                </p>
              </div>
            </div>
            <div className="mt-5 rounded-[1.2rem] border border-white/8 bg-black/16 p-4 text-sm text-white/72">
              {message}
            </div>
          </div>

          <div className="glass-panel rounded-[1.75rem] p-6">
            <h3 className="text-lg font-semibold text-white">运行历史</h3>
            <div className="mt-4 space-y-3">
              {detail.runs.map((run) => (
                <div
                  key={run.id}
                  className="rounded-[1.2rem] border border-white/8 bg-white/3 p-4"
                >
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-white">
                      attempt {run.attemptNo} · {run.provider}
                    </p>
                    <StatusBadge
                      label={run.status}
                      tone={
                        run.status === "finished"
                          ? "success"
                          : run.status === "error"
                            ? "danger"
                            : "accent"
                      }
                    />
                  </div>
                  <p className="mt-3 text-sm text-white/62">
                    {run.gpuType} / runtime {run.runtimeSeconds}s / provider cost {Number(run.providerCost).toFixed(2)}
                  </p>
                  {run.failReason ? (
                    <p className="mt-2 text-sm text-rose-100">{run.failReason}</p>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="space-y-6">
          <div className="glass-panel rounded-[1.75rem] p-6">
            <h3 className="text-lg font-semibold text-white">产物归档</h3>
            <div className="mt-4 space-y-3">
              {detail.artifacts.map((artifact) => (
                <div
                  key={artifact.id}
                  className="rounded-[1.2rem] border border-white/8 bg-white/3 p-4"
                >
                  <p className="font-medium text-white">
                    {artifact.type} · {(artifact.fileSize / 1_000_000).toFixed(1)} MB
                  </p>
                  <p className="mt-2 text-xs text-white/56">{artifact.storagePath}</p>
                  <div className="mt-3 flex items-center gap-3">
                    <button
                      type="button"
                      disabled={isPending}
                      onClick={() =>
                        startTransition(async () => {
                          try {
                            const res = await requestArtifactDownload(task.id, artifact.id);
                            window.open(res.download_url, "_blank", "noopener,noreferrer");
                            setMessage(`artifact #${artifact.id} 已打开下载链接。`);
                          } catch (error) {
                            setMessage(error instanceof Error ? error.message : "下载失败。");
                          }
                        })
                      }
                      className="rounded-full border border-cyan-300/35 px-4 py-2 text-xs text-cyan-100 hover:bg-cyan-300/10 disabled:opacity-60"
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
          </div>

          <div className="glass-panel rounded-[1.75rem] p-6">
            <h3 className="text-lg font-semibold text-white">事件日志</h3>
            <div className="mt-4 space-y-3">
              {detail.events.map((event) => (
                <div
                  key={event.id}
                  className="rounded-[1.2rem] border border-white/8 bg-white/3 p-4"
                >
                  <div className="flex items-center justify-between">
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
                  <p className="mt-2 text-sm leading-6 text-white/62">{event.message}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </ConsoleShell>
  );
}
