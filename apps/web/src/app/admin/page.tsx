"use client";

import Link from "next/link";
import { startTransition, useEffect, useMemo, useState } from "react";

import { ConsoleShell } from "@/components/console-shell";
import {
  fetchAdminTasks,
  fetchBilling,
  fetchCodeEditHistory,
  fetchExecutionHealth,
  fetchMonitoringOverview,
  fetchProviderHealth,
  previewCodeEdit,
  rollbackCodeEdit,
  runCodeEdit,
  runExecutionOnce,
} from "@/lib/api";
import type {
  BillingSnapshot,
  CodeEditHistoryItem,
  MonitoringOverview,
  ProviderHealth,
  TaskItem,
} from "@/lib/mock";

type TestResult = {
  command: string;
  returncode: number;
  stdout: string;
  stderr: string;
};

export default function AdminPage() {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [providers, setProviders] = useState<ProviderHealth[]>([]);
  const [billing, setBilling] = useState<BillingSnapshot | null>(null);
  const [executionHealth, setExecutionHealth] = useState<{
    mode: string;
    status: string;
  } | null>(null);
  const [monitoring, setMonitoring] = useState<MonitoringOverview | null>(null);
  const [history, setHistory] = useState<CodeEditHistoryItem[]>([]);
  const [runMessage, setRunMessage] = useState("尚未触发执行。");
  const [isRunning, setIsRunning] = useState(false);
  const [editInstructions, setEditInstructions] = useState(
    "请根据当前文件内容做最小正确修改，并保持现有风格一致。",
  );
  const [taskId, setTaskId] = useState("");
  const [editFiles, setEditFiles] = useState("apps/api/app/config.py");
  const [testCommands, setTestCommands] = useState(
    "python -m pytest .\\apps\\api\\tests",
  );
  const [editMessage, setEditMessage] = useState("尚未执行代码修改。");
  const [diffPreview, setDiffPreview] = useState("");
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [rollingBackId, setRollingBackId] = useState<number | null>(null);

  const loadDashboard = async () => {
    try {
      const [
        taskBundle,
        providerRows,
        billingRows,
        health,
        historyRows,
        monitoringRows,
      ] = await Promise.all([
        fetchAdminTasks(),
        fetchProviderHealth(),
        fetchBilling(),
        fetchExecutionHealth(),
        fetchCodeEditHistory(),
        fetchMonitoringOverview(),
      ]);
      setTasks(taskBundle.items);
      setProviders(providerRows);
      setBilling(billingRows);
      setExecutionHealth(health);
      setHistory(historyRows);
      setMonitoring(monitoringRows);
    } catch (error) {
      setRunMessage(
        error instanceof Error
          ? error.message
          : "后台加载失败，请先登录管理员账号。",
      );
    }
  };

  useEffect(() => {
    void loadDashboard();
  }, []);

  const summary = useMemo(() => {
    const running = tasks.filter((task) => task.status === "running").length;
    const failed = tasks.filter((task) => task.status === "failed").length;
    return { total: tasks.length, running, failed };
  }, [tasks]);

  const parsedFiles = editFiles
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);

  const parsedTests = testCommands
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);

  const handleRunOnce = async () => {
    setIsRunning(true);
    try {
      const result = await runExecutionOnce();
      const health = await fetchExecutionHealth();
      const monitoringData = await fetchMonitoringOverview();
      startTransition(() => {
        setExecutionHealth(health);
        setMonitoring(monitoringData);
        setRunMessage(`本次执行处理了 ${result.processed_count} 个任务。`);
      });
    } catch (error) {
      setRunMessage(
        error instanceof Error ? error.message : "执行触发失败。",
      );
    } finally {
      setIsRunning(false);
    }
  };

  const handlePreview = async () => {
    setIsPreviewing(true);
    try {
      const result = await previewCodeEdit({
        instructions: editInstructions,
        files: parsedFiles,
      });
      setDiffPreview(result.diff_preview ?? "");
      setEditMessage(
        `${result.summary} 预览涉及 ${result.changed_files.join(", ")}。`,
      );
      setTestResults([]);
    } catch (error) {
      setEditMessage(error instanceof Error ? error.message : "预览失败。");
      setDiffPreview("");
    } finally {
      setIsPreviewing(false);
    }
  };

  const handleCodeEdit = async () => {
    setIsEditing(true);
    try {
      const result = await runCodeEdit({
        instructions: editInstructions,
        files: parsedFiles,
        test_commands: parsedTests,
        task_id: taskId ? Number(taskId) : undefined,
      });
      setEditMessage(
        `${result.summary} 已修改 ${result.changed_files.join(", ")}，共 ${result.operations_count} 个操作。执行记录 #${result.execution_id ?? "--"}${result.task_id ? `，关联任务 #${result.task_id}` : ""}。`,
      );
      setDiffPreview(result.diff_preview ?? "");
      setTestResults((result.test_results ?? []) as TestResult[]);
      await loadDashboard();
    } catch (error) {
      setEditMessage(
        error instanceof Error ? error.message : "代码修改执行失败。",
      );
    } finally {
      setIsEditing(false);
    }
  };

  const handleRollback = async (executionId: number) => {
    setRollingBackId(executionId);
    try {
      const result = await rollbackCodeEdit(executionId);
      setEditMessage(
        `执行记录 #${result.execution_id} 已回滚，恢复文件：${result.restored_files.join(", ")}。`,
      );
      await loadDashboard();
    } catch (error) {
      setEditMessage(error instanceof Error ? error.message : "回滚失败。");
    } finally {
      setRollingBackId(null);
    }
  };

  return (
    <ConsoleShell
      current="/admin"
      eyebrow="Ops Console"
      title="后台总览"
      actions={
        <>
          <Link
            href="/admin/tasks"
            className="rounded-full border border-white/14 px-5 py-3 text-sm text-white/72 hover:bg-white/6"
          >
            任务台
          </Link>
          <Link
            href="/admin/users"
            className="rounded-full border border-white/14 px-5 py-3 text-sm text-white/72 hover:bg-white/6"
          >
            用户权限
          </Link>
          <Link
            href="/admin/providers"
            className="rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-950"
          >
            资源池
          </Link>
        </>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <section className="space-y-6">
          <div className="glass-panel rounded-[1.75rem] p-6">
            <div className="grid gap-4 md:grid-cols-3">
              {[
                { label: "总任务数", value: String(summary.total) },
                { label: "运行中", value: String(summary.running) },
                { label: "失败任务", value: String(summary.failed) },
                {
                  label: "今日收入",
                  value: billing ? billing.revenue.toFixed(2) : "--",
                },
                {
                  label: "今日成本",
                  value: billing ? billing.cost.toFixed(2) : "--",
                },
                {
                  label: "今日毛利",
                  value: billing ? billing.grossProfit.toFixed(2) : "--",
                },
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
          </div>

          <section className="glass-panel rounded-[1.75rem] p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-white/45">
                  Execution Console
                </p>
                <h3 className="mt-2 text-lg font-semibold text-white">
                  执行卡片
                </h3>
              </div>
              <button
                type="button"
                onClick={() => void handleRunOnce()}
                disabled={isRunning}
                className="rounded-full bg-cyan-200 px-5 py-3 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isRunning ? "执行中..." : "执行一次 Worker"}
              </button>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div className="rounded-[1.2rem] border border-white/8 bg-white/3 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-white/45">
                  本地执行状态
                </p>
                <p className="mt-3 text-2xl font-semibold text-white">
                  {executionHealth?.status ?? "--"}
                </p>
                <p className="mt-2 text-sm text-white/58">
                  {executionHealth?.mode ?? "unknown"}
                </p>
              </div>
              <div className="rounded-[1.2rem] border border-white/8 bg-white/3 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-white/45">
                  执行说明
                </p>
                <p className="mt-3 text-sm leading-6 text-white/72">
                  当前后台既能触发 worker，也能预览和执行本地模型代码修改，并在执行后保存审计记录、测试结果和回滚入口。
                </p>
              </div>
            </div>

            <div className="mt-4 rounded-[1.2rem] border border-white/8 bg-black/16 p-4 text-sm text-white/72">
              {runMessage}
            </div>
            {monitoring ? (
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="rounded-[1.2rem] border border-white/8 bg-white/3 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-white/45">Adapter</p>
                  <p className="mt-2 text-sm text-white/80">
                    {monitoring.adapterKey} / {monitoring.marketplaceName}
                  </p>
                  <p className="mt-2 text-xs text-white/58">
                    active_runs {monitoring.activeRuns} / retry_queue {monitoring.queuedForRetry}
                  </p>
                  <p className="mt-1 text-xs text-white/58">
                    cleanup_pending {monitoring.pendingCleanup} / cancelling {monitoring.openCancellations}
                  </p>
                </div>
                <div className="rounded-[1.2rem] border border-white/8 bg-white/3 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-white/45">Runtime Cost</p>
                  <p className="mt-2 text-sm text-white/80">
                    provider_cost {monitoring.recentProviderCost.toFixed(2)}
                  </p>
                  <p className="mt-2 text-xs text-white/58">
                    runtime_seconds {monitoring.recentRuntimeSeconds}
                  </p>
                </div>
              </div>
            ) : null}
          </section>

          <section className="glass-panel rounded-[1.75rem] p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-white/45">
                  Local Code Executor
                </p>
                <h3 className="mt-2 text-lg font-semibold text-white">
                  代码差异执行器
                </h3>
              </div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => void handlePreview()}
                  disabled={isPreviewing}
                  className="rounded-full border border-white/14 px-5 py-3 text-sm text-white/72 hover:bg-white/6 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isPreviewing ? "预览中..." : "预览 Diff"}
                </button>
                <button
                  type="button"
                  onClick={() => void handleCodeEdit()}
                  disabled={isEditing}
                  className="rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isEditing ? "执行中..." : "执行代码修改"}
                </button>
              </div>
            </div>

            <div className="mt-5 grid gap-4">
              <label className="grid gap-2 text-sm text-white/72">
                <span>修改指令</span>
                <textarea
                  value={editInstructions}
                  onChange={(event) => setEditInstructions(event.target.value)}
                  rows={5}
                  className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none"
                />
              </label>

              <label className="grid gap-2 text-sm text-white/72">
                <span>关联任务 ID，可选</span>
                <input
                  value={taskId}
                  onChange={(event) => setTaskId(event.target.value)}
                  placeholder="例如 1024"
                  className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none"
                />
              </label>

              <label className="grid gap-2 text-sm text-white/72">
                <span>目标文件，每行一个</span>
                <textarea
                  value={editFiles}
                  onChange={(event) => setEditFiles(event.target.value)}
                  rows={4}
                  className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none"
                />
              </label>

              <label className="grid gap-2 text-sm text-white/72">
                <span>执行后测试命令，每行一个</span>
                <textarea
                  value={testCommands}
                  onChange={(event) => setTestCommands(event.target.value)}
                  rows={3}
                  className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none"
                />
              </label>
            </div>

            <div className="mt-4 rounded-[1.2rem] border border-white/8 bg-black/16 p-4 text-sm text-white/72">
              {editMessage}
            </div>

            {diffPreview ? (
              <pre className="mt-4 overflow-x-auto rounded-[1.2rem] border border-cyan-200/15 bg-black/30 p-4 text-xs leading-6 text-cyan-50/82">
                {diffPreview}
              </pre>
            ) : null}

            {testResults.length ? (
              <div className="mt-4 space-y-3">
                {testResults.map((result) => (
                  <div
                    key={result.command}
                    className="rounded-[1.2rem] border border-white/8 bg-white/3 p-4"
                  >
                    <p className="text-sm font-medium text-white">
                      {result.command}
                    </p>
                    <p className="mt-2 text-xs text-white/56">
                      return code: {result.returncode}
                    </p>
                    {result.stdout ? (
                      <pre className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 text-xs leading-6 text-white/74">
                        {result.stdout}
                      </pre>
                    ) : null}
                    {result.stderr ? (
                      <pre className="mt-3 overflow-x-auto rounded-xl bg-rose-950/30 p-3 text-xs leading-6 text-rose-100/80">
                        {result.stderr}
                      </pre>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : null}
          </section>

          <section className="glass-panel rounded-[1.75rem] p-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-white/45">
                  Audit Trail
                </p>
                <h3 className="mt-2 text-lg font-semibold text-white">
                  代码执行历史
                </h3>
              </div>
              <span className="text-sm text-white/56">
                最近 {history.length} 条记录
              </span>
            </div>

            <div className="mt-5 space-y-4">
              {history.length ? (
                history.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-[1.25rem] border border-white/8 bg-white/3 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-white">
                          #{item.id} {item.summary ?? "本地模型代码执行"}
                        </p>
                    <p className="mt-2 text-xs text-white/56">
                      操作者 {item.actorEmail ?? "unknown"} · 状态{" "}
                      {item.status} · 回滚 {item.rollbackStatus}
                    </p>
                    {item.taskId ? (
                      <p className="mt-1 text-xs text-cyan-100/75">
                        任务 #{item.taskId} · 链 #{item.reviewChainId ?? "--"} · step {item.chainStepNo ?? "--"} ·
                        {item.reviewChainStatus ?? "--"} · 阶段 {item.workflowStage ?? "--"} · review round {item.reviewRound ?? 0} ·
                        {item.reviewApproved == null
                          ? " 审查待定"
                          : item.reviewApproved
                            ? " 审查通过"
                            : " 审查未通过"}
                      </p>
                    ) : null}
                      </div>
                      <button
                        type="button"
                        onClick={() => void handleRollback(item.id)}
                        disabled={
                          item.rollbackStatus === "completed" ||
                          rollingBackId === item.id
                        }
                        className="rounded-full border border-white/14 px-4 py-2 text-xs text-white/72 hover:bg-white/6 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {rollingBackId === item.id ? "回滚中..." : "回滚本次修改"}
                      </button>
                    </div>

                    <p className="mt-3 text-sm leading-6 text-white/72">
                      {item.instructions}
                    </p>
                    <p className="mt-3 text-xs text-white/56">
                      目标文件: {item.requestedFiles.join(", ") || "--"}
                    </p>
                    <p className="mt-1 text-xs text-white/56">
                      实际改动: {item.changedFiles.join(", ") || "--"}
                    </p>
                    <p className="mt-1 text-xs text-white/56">
                      创建时间: {new Date(item.createdAt).toLocaleString()}
                    </p>
                    {item.rolledBackAt ? (
                      <p className="mt-1 text-xs text-amber-200/80">
                        已回滚于 {new Date(item.rolledBackAt).toLocaleString()}
                      </p>
                    ) : null}
                    {item.rollbackError ? (
                      <p className="mt-1 text-xs text-rose-200/80">
                        回滚错误: {item.rollbackError}
                      </p>
                    ) : null}
                    {item.diffPreview ? (
                      <pre className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 text-[11px] leading-6 text-cyan-50/82">
                        {item.diffPreview}
                      </pre>
                    ) : null}
                  </div>
                ))
              ) : (
                <div className="rounded-[1.25rem] border border-dashed border-white/12 bg-black/10 p-5 text-sm text-white/56">
                  还没有代码执行历史。首次执行后，这里会显示审计记录、diff 和回滚状态。
                </div>
              )}
            </div>
          </section>
        </section>

        <section className="glass-panel rounded-[1.75rem] p-6">
          <p className="text-xs uppercase tracking-[0.22em] text-white/45">
            Provider Snapshot
          </p>
          <div className="mt-5 space-y-3">
            {providers.map((provider) => (
              <div
                key={provider.provider}
                className="rounded-[1.2rem] border border-white/8 bg-white/3 px-4 py-4"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-white">
                    {provider.provider}
                  </span>
                  <span className="text-sm text-white/56">
                    {provider.offerCount} offers
                  </span>
                </div>
                <p className="mt-2 text-sm text-white/58">
                  可靠性 {provider.averageReliability.toFixed(2)} · 成功率{" "}
                  {(provider.averageSuccessRate * 100).toFixed(0)}%
                </p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </ConsoleShell>
  );
}
