"use client";

import { FormEvent, useEffect, useState, useTransition } from "react";

import { ConsoleShell } from "@/components/console-shell";
import { fetchWallet, rechargeWallet } from "@/lib/api";

export default function WalletPage() {
  const [amount, setAmount] = useState(100);
  const [walletBundle, setWalletBundle] = useState<Awaited<ReturnType<typeof fetchWallet>> | null>(null);
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    void fetchWallet().then(setWalletBundle);
  }, []);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    startTransition(async () => {
      try {
        await rechargeWallet(amount);
        const next = await fetchWallet();
        setWalletBundle(next);
      } catch (rechargeError) {
        setError(
          rechargeError instanceof Error
            ? rechargeError.message
            : "充值失败，请确认 API 已启动并已登录。",
        );
      }
    });
  }

  return (
    <ConsoleShell current="/wallet" eyebrow="Wallet Surface" title="钱包与流水">
      <div className="grid gap-6 xl:grid-cols-[0.84fr_1.16fr]">
        <section className="glass-panel rounded-[1.75rem] p-6">
          <p className="text-xs uppercase tracking-[0.22em] text-white/45">Balance</p>
          <p className="display-font mt-4 text-5xl font-semibold text-white">
            {walletBundle ? walletBundle.wallet.balance.toFixed(2) : "--"}
          </p>
          <p className="mt-3 text-sm text-white/58">
            冻结金额 {walletBundle ? walletBundle.wallet.frozenBalance.toFixed(2) : "--"}{" "}
            {walletBundle?.wallet.currency ?? "CNY"}
          </p>

          <form onSubmit={onSubmit} className="mt-8 space-y-4">
            <label className="block text-sm text-white/72">充值金额</label>
            <input
              type="number"
              value={amount}
              onChange={(event) => setAmount(Number(event.target.value))}
              className="w-full rounded-[1rem] border border-white/12 bg-white/4 px-4 py-3 text-white outline-none"
            />
            {error ? (
              <div className="rounded-[1rem] border border-rose-400/25 bg-rose-400/10 px-4 py-3 text-sm text-rose-100">
                {error}
              </div>
            ) : null}
            <button
              type="submit"
              disabled={isPending}
              className="display-font rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-950 disabled:opacity-70"
            >
              {isPending ? "处理中..." : "立即充值"}
            </button>
          </form>
        </section>

        <section className="glass-panel rounded-[1.75rem] p-6">
          <h3 className="text-lg font-semibold text-white">流水记录</h3>
          <div className="mt-5 overflow-x-auto">
            <table className="min-w-full text-left text-sm text-white/72">
              <thead className="text-xs uppercase tracking-[0.18em] text-white/38">
                <tr>
                  <th className="pb-3">类型</th>
                  <th className="pb-3">金额</th>
                  <th className="pb-3">余额变动后</th>
                  <th className="pb-3">关联对象</th>
                  <th className="pb-3">时间</th>
                </tr>
              </thead>
              <tbody>
                {walletBundle?.ledger.map((item) => (
                  <tr key={item.id} className="border-t border-white/8">
                    <td className="py-4">{item.type}</td>
                    <td className="py-4">{item.amount.toFixed(2)}</td>
                    <td className="py-4">{item.balanceAfter.toFixed(2)}</td>
                    <td className="py-4">{item.refId ?? "--"}</td>
                    <td className="py-4 text-white/46">{new Date(item.createdAt).toLocaleString()}</td>
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
