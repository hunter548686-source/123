import Link from "next/link";
import { ReactNode } from "react";

const navItems = [
  { href: "/dashboard", label: "总览" },
  { href: "/tasks", label: "任务" },
  { href: "/tasks/new", label: "新建任务" },
  { href: "/wallet", label: "钱包" },
  { href: "/billing", label: "账单" },
  { href: "/admin", label: "后台" },
  { href: "/admin/tasks", label: "后台任务" },
  { href: "/admin/users", label: "用户权限" },
  { href: "/admin/providers", label: "供给池" },
];

export function ConsoleShell({
  title,
  eyebrow,
  current,
  children,
  actions,
}: {
  title: string;
  eyebrow: string;
  current: string;
  children: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto grid min-h-screen max-w-[1600px] gap-6 px-4 py-4 lg:grid-cols-[280px_minmax(0,1fr)] lg:px-6">
        <aside className="glass-panel shell-grid rounded-[2rem] p-6">
          <Link href="/" className="block">
            <p className="display-font text-sm uppercase tracking-[0.34em] text-cyan-100/70">
              StableGPU
            </p>
            <h1 className="display-font mt-3 text-3xl font-semibold text-white">
              算力管家
            </h1>
            <p className="mt-3 max-w-xs text-sm leading-7 text-white/58">
              不是卖卡，而是把 AI 视频任务稳定交付出去。
            </p>
          </Link>

          <div className="mt-8 rounded-[1.5rem] border border-white/8 bg-black/18 p-4">
            <p className="text-xs uppercase tracking-[0.26em] text-white/42">固定角色</p>
            <div className="mt-4 space-y-3 text-sm text-white/72">
              <div className="flex items-center justify-between">
                <span>规划</span>
                <span className="text-cyan-200">GPT-5.4</span>
              </div>
              <div className="flex items-center justify-between">
                <span>执行层</span>
                <span className="text-cyan-200">Provider + Worker</span>
              </div>
              <div className="flex items-center justify-between">
                <span>审查</span>
                <span className="text-cyan-200">GPT-5.4</span>
              </div>
            </div>
          </div>

          <nav className="mt-8 space-y-2">
            {navItems.map((item) => {
              const active = current === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center justify-between rounded-[1rem] px-4 py-3 text-sm transition ${
                    active
                      ? "bg-white/10 text-white"
                      : "text-white/58 hover:bg-white/6 hover:text-white/86"
                  }`}
                >
                  <span>{item.label}</span>
                  <span className="text-[10px] uppercase tracking-[0.2em]">
                    {active ? "open" : "go"}
                  </span>
                </Link>
              );
            })}
          </nav>
        </aside>

        <main className="rounded-[2rem] border border-white/8 bg-[linear-gradient(180deg,rgba(13,26,36,0.9),rgba(7,17,26,0.96))] p-4 shadow-[0_20px_70px_rgba(3,10,20,0.32)] lg:p-8">
          <header className="mb-8 flex flex-col gap-4 border-b border-white/8 pb-6 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.32em] text-cyan-100/68">{eyebrow}</p>
              <h2 className="display-font mt-3 text-3xl font-semibold text-white lg:text-4xl">
                {title}
              </h2>
            </div>
            {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
          </header>
          {children}
        </main>
      </div>
    </div>
  );
}
