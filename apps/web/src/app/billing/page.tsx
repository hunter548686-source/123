"use client";

import { useEffect, useState } from "react";

import { ConsoleShell } from "@/components/console-shell";
import { fetchBilling, fetchTasks } from "@/lib/api";
import type { BillingSnapshot, TaskItem } from "@/lib/mock";

export default function BillingPage() {
  const [billing, setBilling] = useState<BillingSnapshot | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);

  useEffect(() => {
    void Promise.all([fetchBilling(), fetchTasks()]).then(([billingData, taskRows]) => {
      setBilling(billingData);
      setTasks(taskRows);
    });
  }, []);

  return (
    <ConsoleShell current="/billing" eyebrow="Billing Surface" title="账单与毛利">
      <div className="grid gap-6 xl:grid-cols-[0.88fr_1.12fr]">
        <section className="glass-panel rounded-[1.75rem] p-6">
          <div className="grid gap-4 md:grid-cols-2">
            {[
              { label: "总收入", value: billing ? billing.revenue.toFixed(2) : "--" },
              { label: "总成本", value: billing ? billing.cost.toFixed(2) : "--" },
              { label: "总毛利", value: billing ? billing.grossProfit.toFixed(2) : "--" },
              { label: "毛利率", value: billing ? `${billing.grossMargin.toFixed(2)}%` : "--" },
            ].map((item) => (
              <div key={item.label} className="rounded-[1.3rem] border border-white/8 bg-white/4 p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-white/45">{item.label}</p>
                <p className="display-font mt-4 text-3xl font-semibold text-white">{item.value}</p>
              </div>
            ))}
          </div>
          <div className="mt-6 space-y-3">
            {billing?.byProvider.map((provider) => (
              <div key={provider.provider} className="rounded-[1.2rem] border border-white/8 bg-white/3 px-4 py-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-white">{provider.provider}</span>
                  <span className="text-sm text-white/58">{provider.runCount} runs</span>
                </div>
                <p className="mt-2 text-sm text-white/58">累计成本 {provider.cost.toFixed(2)}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="glass-panel rounded-[1.75rem] p-6">
          <h3 className="text-lg font-semibold text-white">任务账单明细</h3>
          <div className="mt-5 overflow-x-auto">
            <table className="min-w-full text-left text-sm text-white/72">
              <thead className="text-xs uppercase tracking-[0.18em] text-white/38">
                <tr>
                  <th className="pb-3">任务</th>
                  <th className="pb-3">报价</th>
                  <th className="pb-3">实际扣费</th>
                  <th className="pb-3">成本</th>
                  <th className="pb-3">状态</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.id} className="border-t border-white/8">
                    <td className="py-4">#{task.id}</td>
                    <td className="py-4">{(task.quotedPrice ?? 0).toFixed(2)}</td>
                    <td className="py-4">{task.finalCharge ? task.finalCharge.toFixed(2) : "--"}</td>
                    <td className="py-4">{task.finalCost ? task.finalCost.toFixed(2) : "--"}</td>
                    <td className="py-4">{task.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </ConsoleShell>
  );
}
