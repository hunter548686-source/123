"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, useTransition } from "react";

import { ConsoleShell } from "@/components/console-shell";
import { StatusBadge } from "@/components/status-badge";
import { cancelAdminTask, fetchAdminTasks, retryAdminTask } from "@/lib/api";
import type { AdminTaskBundle, TaskItem } from "@/lib/mock";

export default function AdminTasksPage() {
  const [bundle, setBundle] = useState<AdminTaskBundle | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [message, setMessage] = useState("可在此查看全量任务并手动干预。");
  const [isPending, startTransition] = useTransition();

  const loadTasks = async () => {
    const next = await fetchAdminTasks();
    setBundle(next);
  };

  useEffect(() => {
    let alive = true;
    void fetchAdminTasks()
      .then((next) => {
        if (alive) setBundle(next);
      })
      .catch((error) => {
        if (alive) {
          setMessage(
            error instanceof Error ? error.message : "加载后台任务失败，请先登录管理员账号。",
          );
        }
      });
    return () => {
      alive = false;
    };
  }, []);

  const filteredTasks = useMemo(() => {
    if (!bundle) return [];
    if (statusFilter === "all") return bundle.items;
    return bundle.items.filter((task) => task.status === statusFilter);
  }, [bundle, statusFilter]);

  const summary = bundle?.summary ?? {
    total: 0,
    running: 0,
    failed: 0,
    completed: 0,
  };

  const statuses = useMemo(() => {
    if (!bundle) return ["all"];
    return ["all", ...new Set(bundle.items.map((item) => item.status))];
  }, [bundle]);

  const runAction = (taskId: number, action: "retry" | "cancel") => {
    startTransition(async () => {
      try {
        if (action === "retry") {
          await retryAdminTask(String(taskId));
        } else {
          await cancelAdminTask(String(taskId));
        }
        await loadTasks();
        setMessage(`任务 #${taskId} 已触发 ${action === "retry" ? "重试" : "取消"}。`);
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "操作失败。");
      }
    });
  };

  const actionDisabled = (task: TaskItem, action: "retry" | "cancel") => {
    if (action === "retry") {
      return ["completed", "cancelled"].includes(task.status);
    }
    return ["completed", "cancelled", "failed"].includes(task.status);
  };

  return (
    <ConsoleShell
      current="/admin/tasks"
      eyebrow="Ops Queue"
      title="后台任务台"
      actions={
        <Link
          href="/admin"
          className="rounded-full border border-white/14 px-5 py-3 text-sm text-white/72 hover:bg-white/6"
        >
          返回后台总览
        </Link>
      }
    >
      <section className="glass-panel rounded-[1.75rem] p-6">
        <div className="grid gap-4 md:grid-cols-4">
          {[
            { label: "总任务", value: summary.total },
            { label: "运行中", value: summary.running },
            { label: "失败", value: summary.failed },
            { label: "已完成", value: summary.completed },
          ].map((item) => (
            <div
              key={item.label}
              className="rounded-[1.3rem] border border-white/8 bg-white/4 p-4"
            >
              <p className="text-xs uppercase tracking-[0.22em] text-white/45">
                {item.label}
              </p>
              <p className="display-font mt-4 text-3xl font-semibold text-white">
                {item.value}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <label className="text-sm text-white/68">状态筛选</label>
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="rounded-full border border-white/14 bg-black/20 px-4 py-2 text-sm text-white outline-none"
          >
            {statuses.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
          <p className="text-xs text-white/52">{message}</p>
        </div>

        <div className="mt-5 overflow-x-auto">
          <table className="min-w-full text-left text-sm text-white/72">
            <thead className="text-xs uppercase tracking-[0.18em] text-white/38">
              <tr>
                <th className="pb-3">任务</th>
                <th className="pb-3">用户</th>
                <th className="pb-3">Provider</th>
                <th className="pb-3">阶段</th>
                <th className="pb-3">审查</th>
                <th className="pb-3">成本</th>
                <th className="pb-3">更新时间</th>
                <th className="pb-3">操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredTasks.map((task) => (
                <tr key={task.id} className="border-t border-white/8 align-top">
                  <td className="py-4">
                    <Link
                      href={`/admin/tasks/${task.id}`}
                      className="font-medium text-white hover:text-cyan-100"
                    >
                      #{task.id} · {task.taskType}
                    </Link>
                    <p className="mt-1 text-xs text-white/42">{task.templateId}</p>
                  </td>
                  <td className="py-4">user-{task.userId}</td>
                  <td className="py-4">{task.selectedProvider ?? "待调度"}</td>
                  <td className="py-4">
                    <StatusBadge
                      label={`${task.workflowStage} / ${task.status}`}
                      tone={
                        task.status === "failed"
                          ? "danger"
                          : task.status === "running"
                            ? "accent"
                            : task.status === "completed"
                              ? "success"
                              : "neutral"
                      }
                    />
                  </td>
                  <td className="py-4">
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
                  </td>
                  <td className="py-4">
                    {(task.finalCost ?? 0).toFixed(2)} / {(task.finalCharge ?? 0).toFixed(2)}
                  </td>
                  <td className="py-4 text-white/52">
                    {new Date(task.updatedAt).toLocaleString()}
                  </td>
                  <td className="py-4">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={isPending || actionDisabled(task, "retry")}
                        onClick={() => runAction(task.id, "retry")}
                        className="rounded-full border border-white/14 px-3 py-1 text-xs text-white/72 hover:bg-white/6 disabled:opacity-50"
                      >
                        重试
                      </button>
                      <button
                        type="button"
                        disabled={isPending || actionDisabled(task, "cancel")}
                        onClick={() => runAction(task.id, "cancel")}
                        className="rounded-full border border-rose-400/20 px-3 py-1 text-xs text-rose-100 hover:bg-rose-400/10 disabled:opacity-50"
                      >
                        取消
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </ConsoleShell>
  );
}
