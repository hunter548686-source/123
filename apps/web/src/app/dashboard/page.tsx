"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ConsoleShell } from "@/components/console-shell";
import { StageTrack } from "@/components/stage-track";
import { StatusBadge } from "@/components/status-badge";
import { fetchProviderHealth, fetchTasks, fetchWallet } from "@/lib/api";
import type { ProviderHealth, TaskItem, WalletData } from "@/lib/mock";

export default function DashboardPage() {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [wallet, setWallet] = useState<WalletData | null>(null);
  const [providers, setProviders] = useState<ProviderHealth[]>([]);

  useEffect(() => {
    void Promise.all([fetchTasks(), fetchWallet(), fetchProviderHealth()]).then(
      ([taskRows, walletBundle, providerRows]) => {
        setTasks(taskRows);
        setWallet(walletBundle.wallet);
        setProviders(providerRows);
      },
    );
  }, []);

  const runningTask = useMemo(
    () => tasks.find((task) => task.status === "running") ?? tasks[0],
    [tasks],
  );

  const metrics = useMemo(() => {
    const running = tasks.filter((task) => task.status === "running").length;
    const completed = tasks.filter((task) => task.status === "completed").length;
    const successRate = tasks.length ? Math.round((completed / tasks.length) * 100) : 0;
    const spend = tasks.reduce((sum, task) => sum + Number(task.finalCharge ?? task.quotedPrice ?? 0), 0);
    return { running, completed, successRate, spend };
  }, [tasks]);

  return (
    <ConsoleShell
      current="/dashboard"
      eyebrow="Task Delivery Console"
      title="控制台总览"
      actions={
        <>
          <Link href="/tasks/new" className="rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-950">
            新建任务
          </Link>
          <Link href="/admin" className="rounded-full border border-white/14 px-5 py-3 text-sm text-white/72 hover:bg-white/6">
            打开后台
          </Link>
        </>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <section className="glass-panel rounded-[1.75rem] p-6">
          <div className="grid gap-4 md:grid-cols-4">
            {[
              { label: "当前余额", value: wallet ? `${wallet.balance.toFixed(2)} ${wallet.currency}` : "--" },
              { label: "运行中任务", value: String(metrics.running) },
              { label: "今日完成任务", value: String(metrics.completed) },
              { label: "近 7 日成功率", value: `${metrics.successRate}%` },
            ].map((item) => (
              <div key={item.label} className="rounded-[1.35rem] border border-white/8 bg-white/4 p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-white/45">{item.label}</p>
                <p className="display-font mt-4 text-3xl font-semibold text-white">{item.value}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 rounded-[1.45rem] border border-white/8 bg-black/16 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-white/45">最近任务</p>
                <h3 className="mt-2 text-lg font-semibold text-white">交付队列</h3>
              </div>
              <StatusBadge label={`今日支出 ${metrics.spend.toFixed(2)} CNY`} tone="accent" />
            </div>

            <div className="mt-5 overflow-x-auto">
              <table className="min-w-full text-left text-sm text-white/72">
                <thead className="text-xs uppercase tracking-[0.18em] text-white/38">
                  <tr>
                    <th className="pb-3">任务</th>
                    <th className="pb-3">策略</th>
                    <th className="pb-3">状态</th>
                    <th className="pb-3">Provider</th>
                    <th className="pb-3">进度</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.map((task) => (
                    <tr key={task.id} className="border-t border-white/8">
                      <td className="py-3">
                        <Link href={`/tasks/${task.id}`} className="font-medium text-white hover:text-cyan-100">
                          #{task.id} · {task.taskType.replaceAll("_", " ")}
                        </Link>
                      </td>
                      <td className="py-3 uppercase text-white/56">{task.strategy}</td>
                      <td className="py-3">
                        <StatusBadge
                          label={task.status}
                          tone={task.status === "completed" ? "success" : task.status === "running" ? "accent" : "warning"}
                        />
                      </td>
                      <td className="py-3">{task.selectedProvider ?? "待调度"}</td>
                      <td className="py-3">{task.progress}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <div className="space-y-6">
          {runningTask ? (
            <StageTrack
              planning={runningTask.planningStatus}
              execution={runningTask.executionStatus}
              review={runningTask.reviewStatus}
              currentStage={runningTask.workflowStage}
            />
          ) : null}

          <section className="glass-panel rounded-[1.75rem] p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-white/45">Provider Health</p>
                <h3 className="mt-2 text-lg font-semibold text-white">调度候选池</h3>
              </div>
              <Link href="/admin/providers" className="text-sm text-cyan-100/80">
                查看全部
              </Link>
            </div>
            <div className="mt-5 space-y-3">
              {providers.map((provider) => (
                <div key={provider.provider} className="rounded-[1.2rem] border border-white/8 bg-white/3 px-4 py-4">
                  <div className="flex items-center justify-between">
                    <p className="text-base font-medium text-white">{provider.provider}</p>
                    <StatusBadge label={`${Math.round(provider.averageSuccessRate * 100)}% success`} tone="success" />
                  </div>
                  <p className="mt-3 text-sm text-white/58">
                    平均价 ${provider.averagePricePerHour.toFixed(2)} /h · 启动评分 {provider.averageStartupScore.toFixed(2)}
                  </p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </ConsoleShell>
  );
}
