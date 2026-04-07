"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ConsoleShell } from "@/components/console-shell";
import { StatusBadge } from "@/components/status-badge";
import { fetchTasks } from "@/lib/api";
import type { TaskItem } from "@/lib/mock";

export default function TasksPage() {
  const [tasks, setTasks] = useState<TaskItem[]>([]);

  useEffect(() => {
    void fetchTasks().then(setTasks);
  }, []);

  return (
    <ConsoleShell
      current="/tasks"
      eyebrow="Queue Surface"
      title="任务列表"
      actions={
        <Link href="/tasks/new" className="rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-950">
          新建任务
        </Link>
      }
    >
      <section className="glass-panel rounded-[1.75rem] p-6">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm text-white/72">
            <thead className="text-xs uppercase tracking-[0.18em] text-white/38">
              <tr>
                <th className="pb-3">任务</th>
                <th className="pb-3">策略</th>
                <th className="pb-3">阶段</th>
                <th className="pb-3">Provider</th>
                <th className="pb-3">报价</th>
                <th className="pb-3">实际扣费</th>
                <th className="pb-3">更新时间</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.id} className="border-t border-white/8">
                  <td className="py-4">
                    <Link href={`/tasks/${task.id}`} className="font-medium text-white hover:text-cyan-100">
                      #{task.id} · {task.taskType.replaceAll("_", " ")}
                    </Link>
                    <p className="mt-1 text-xs text-white/42">{task.templateId}</p>
                  </td>
                  <td className="py-4 uppercase text-white/56">{task.strategy}</td>
                  <td className="py-4">
                    <StatusBadge
                      label={`${task.workflowStage} / ${task.status}`}
                      tone={task.status === "completed" ? "success" : task.status === "running" ? "accent" : "warning"}
                    />
                  </td>
                  <td className="py-4">{task.selectedProvider ?? "待调度"}</td>
                  <td className="py-4">{(task.quotedPrice ?? 0).toFixed(2)}</td>
                  <td className="py-4">{task.finalCharge ? task.finalCharge.toFixed(2) : "--"}</td>
                  <td className="py-4 text-white/46">{new Date(task.updatedAt).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </ConsoleShell>
  );
}
