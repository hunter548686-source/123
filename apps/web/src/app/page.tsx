"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchHomeMetrics } from "@/lib/api";
import type { HomeMetrics } from "@/lib/mock";

function formatDuration(totalSeconds: number): string {
  if (!totalSeconds || totalSeconds <= 0) return "--";
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes <= 0) return `${seconds}s`;
  return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

export default function Home() {
  const [homeMetrics, setHomeMetrics] = useState<HomeMetrics | null>(null);

  useEffect(() => {
    void fetchHomeMetrics().then(setHomeMetrics);
  }, []);

  const sampleSizeText =
    homeMetrics && homeMetrics.sampleSize7d > 0
      ? `近 7 日收口 ${homeMetrics.sampleSize7d} 个任务`
      : "近 7 日暂无收口任务";

  const updatedAtText = homeMetrics
    ? `更新于 ${new Date(homeMetrics.updatedAt).toLocaleString("zh-CN", { hour12: false })}`
    : "等待 API 返回";

  const valueCards = [
    {
      title: "平均交付时长",
      value: homeMetrics ? formatDuration(homeMetrics.averageDeliverySeconds) : "--",
      note: "来自真实运行任务的平均 runtime_seconds",
    },
    {
      title: "7 日任务完成率",
      value: homeMetrics ? `${homeMetrics.successRate7d.toFixed(1)}%` : "--",
      note: sampleSizeText,
    },
    {
      title: "可用 Provider",
      value: homeMetrics ? String(homeMetrics.providerCount) : "--",
      note: "基于最新 offers 快照统计",
    },
    {
      title: "成本可视化覆盖",
      value: homeMetrics ? `${homeMetrics.costVisibilityCoverage.toFixed(1)}%` : "--",
      note: updatedAtText,
    },
  ];

  const deliverySteps = [
    {
      id: "01",
      title: "创建任务并实时拿报价",
      body: "输入 prompt、时长与分辨率后，系统返回推荐执行路径与风险提示，不需要手工比卡。",
    },
    {
      id: "02",
      title: "调度器自动选机与下发",
      body: "按价格、稳定性、启动速度和历史成功率综合评分，自动选择 provider 并发起执行。",
    },
    {
      id: "03",
      title: "失败自动重试与迁移",
      body: "执行异常会触发取消、清理、迁移和重试链路，确保任务持续推进而不是挂起。",
    },
    {
      id: "04",
      title: "结果归档并可下载",
      body: "交付结果、成本、日志、审查结论统一沉淀，可在任务详情页直接下载产物。",
    },
  ];

  const capabilityCards = [
    {
      title: "自动比价选机",
      body: "实时比较可用供给，不让用户面对底层 GPU 选择复杂度。",
    },
    {
      title: "完整状态机",
      body: "支持 running / retrying / cancelling / cleaning_up / completed / failed 全流程状态。",
    },
    {
      title: "失败恢复链路",
      body: "失败时自动执行 cancel -> cleanup -> retry/fail，避免残留资源和重复扣费。",
    },
    {
      title: "可运营监控",
      body: "后台可查看 provider 健康度、成功率、重试数、任务成本与结果归档状态。",
    },
  ];

  return (
    <main className="hero-glow min-h-screen overflow-hidden">
      <section className="shell-grid border-b border-white/8 px-5 pb-16 pt-5 sm:px-8 lg:px-12">
        <nav className="mx-auto flex max-w-[1500px] items-center justify-between rounded-full border border-white/10 bg-white/4 px-5 py-3 backdrop-blur">
          <div>
            <p className="display-font text-sm uppercase tracking-[0.34em] text-cyan-100/70">
              StableGPU
            </p>
          </div>
          <div className="hidden gap-6 text-sm text-white/65 md:flex">
            <Link href="#delivery">交付链路</Link>
            <Link href="#proof">稳定能力</Link>
            <Link href="#ops">控制台</Link>
          </div>
          <div className="flex gap-3">
            <Link href="/login" className="rounded-full border border-white/14 px-4 py-2 text-sm text-white/72 hover:bg-white/6">
              登录
            </Link>
            <Link href="/tasks/new" className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-950">
              立即开始
            </Link>
          </div>
        </nav>

        <div className="fade-up mx-auto mt-14 grid max-w-[1500px] gap-10 lg:min-h-[calc(100svh-140px)] lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.36em] text-cyan-100/70">
              AI 视频任务稳定交付平台
            </p>
            <h1 className="display-font mt-6 text-[clamp(3.2rem,8vw,7rem)] font-semibold leading-[0.94] tracking-[-0.05em] text-white">
              用户只关心
              <br />
              任务是否按时完成。
            </h1>
            <p className="mt-8 max-w-xl text-lg leading-8 text-white/68">
              这个系统把“比价、选机、重试、迁移、归档、成本统计”全部自动化，让 AI 视频任务从下单到交付可追踪、可审查、可运营。
            </p>
            <div className="mt-10 flex flex-wrap gap-4">
              <Link href="/tasks/new" className="display-font rounded-full bg-white px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-100">
                创建任务
              </Link>
              <Link href="/tasks" className="rounded-full border border-white/14 px-6 py-3 text-sm text-white/72 transition hover:bg-white/6">
                查看任务列表
              </Link>
            </div>
          </div>

          <div className="glass-panel rounded-[2rem] p-6 lg:p-8">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-white/45">Live Metrics</p>
                <h2 className="display-font mt-3 text-2xl font-semibold text-white">交付能力一眼可见</h2>
              </div>
              <span className="rounded-full border border-cyan-300/30 bg-cyan-400/10 px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-cyan-100">
                production ready
              </span>
            </div>

            <div className="mt-8 grid gap-4 md:grid-cols-2">
              {valueCards.map((item) => (
                <div key={item.title} className="rounded-[1.4rem] border border-white/8 bg-white/3 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-white/42">{item.title}</p>
                  <p className="display-font mt-4 text-3xl font-semibold text-white">{item.value}</p>
                  <p className="mt-3 text-sm leading-6 text-white/58">{item.note}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="proof" className="mx-auto grid max-w-[1500px] gap-8 px-5 py-16 sm:px-8 lg:grid-cols-3 lg:px-12">
        {capabilityCards.map((item) => (
          <article key={item.title} className="border-t border-white/10 pt-6">
            <h3 className="display-font text-2xl font-semibold text-white">{item.title}</h3>
            <p className="mt-4 max-w-sm text-sm leading-7 text-white/62">{item.body}</p>
          </article>
        ))}
      </section>

      <section id="delivery" className="mx-auto grid max-w-[1500px] gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[0.88fr_1.12fr] lg:px-12">
        <div>
          <p className="text-xs uppercase tracking-[0.34em] text-cyan-100/70">Delivery Path</p>
          <h2 className="display-font mt-4 text-4xl font-semibold text-white">从下单到交付的标准闭环</h2>
        </div>
        <div className="space-y-5">
          {deliverySteps.map((item) => (
            <div key={item.id} className="border-t border-white/8 pt-4">
              <div className="flex items-start gap-4">
                <span className="display-font text-lg text-white/32">{item.id}</span>
                <div>
                  <h3 className="text-base font-semibold text-white">{item.title}</h3>
                  <p className="mt-1 text-base leading-8 text-white/66">{item.body}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section id="ops" className="border-t border-white/8 px-5 py-16 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-[1500px] flex-col items-start justify-between gap-6 lg:flex-row lg:items-end">
          <div>
            <p className="text-xs uppercase tracking-[0.34em] text-cyan-100/70">Ops Ready</p>
            <h2 className="display-font mt-4 text-4xl font-semibold text-white">交付、成本、状态都在一个后台闭环。</h2>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link href="/dashboard" className="rounded-full border border-white/14 px-5 py-3 text-sm text-white/72 hover:bg-white/6">
              打开控制台
            </Link>
            <Link href="/tasks" className="rounded-full border border-white/14 px-5 py-3 text-sm text-white/72 hover:bg-white/6">
              任务列表
            </Link>
            <Link href="/billing" className="rounded-full border border-white/14 px-5 py-3 text-sm text-white/72 hover:bg-white/6">
              账单中心
            </Link>
            <Link href="/admin" className="rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-950">
              运维后台
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
