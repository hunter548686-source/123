"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState, useTransition } from "react";

import { login, register, saveToken } from "@/lib/api";

export function AuthPanel({ defaultMode = "login" }: { defaultMode?: "login" | "register" }) {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">(defaultMode);
  const [email, setEmail] = useState("owner@example.com");
  const [phone, setPhone] = useState("13800000000");
  const [password, setPassword] = useState("pass1234");
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  const summary = useMemo(
    () =>
      mode === "login"
        ? "登录后可直接查看 dashboard、任务历史与 provider 调度状态。"
        : "首个注册用户会自动成为 admin，并自动创建默认钱包与项目。",
    [mode],
  );

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    startTransition(async () => {
      try {
        const response =
          mode === "login"
            ? await login(email, password)
            : await register(email, phone, password);
        saveToken(response.access_token);
        router.push("/dashboard");
      } catch (submitError) {
        setError(
          submitError instanceof Error
            ? submitError.message
            : "认证失败，请检查 API 是否已启动。",
        );
      }
    });
  }

  return (
    <section className="glass-panel fade-up mx-auto max-w-[1080px] overflow-hidden rounded-[2rem]">
      <div className="grid lg:grid-cols-[0.96fr_1.04fr]">
        <div className="shell-grid border-b border-white/8 p-8 lg:border-b-0 lg:border-r lg:p-12">
          <p className="display-font text-sm uppercase tracking-[0.34em] text-cyan-100/68">
            Access Layer
          </p>
          <h1 className="display-font mt-5 text-4xl font-semibold leading-tight text-white md:text-5xl">
            {mode === "login" ? "进入控制台" : "初始化团队"}
          </h1>
          <p className="mt-6 max-w-lg text-base leading-8 text-white/68">{summary}</p>

          <div className="mt-10 space-y-4 text-sm text-white/72">
            <div className="rounded-[1.4rem] border border-white/8 bg-white/4 p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-white/45">固定工作流</p>
              <p className="mt-2">规划：GPT-5.4，执行层：WSL + Ollama，审查：GPT-5.4。</p>
            </div>
            <div className="rounded-[1.4rem] border border-white/8 bg-white/4 p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-white/45">演示账号</p>
              <p className="mt-2">默认可以直接使用 `owner@example.com / pass1234` 走通测试闭环。</p>
            </div>
          </div>

          <div className="mt-8 flex gap-3 text-sm text-white/62">
            <Link href="/" className="rounded-full border border-white/14 px-4 py-2 hover:bg-white/6">
              返回首页
            </Link>
            <Link href="/tasks/new" className="rounded-full border border-white/14 px-4 py-2 hover:bg-white/6">
              查看创建页
            </Link>
          </div>
        </div>

        <div className="p-8 lg:p-12">
          <div className="flex gap-2">
            {[
              { key: "login", label: "登录" },
              { key: "register", label: "注册" },
            ].map((tab) => {
              const active = mode === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setMode(tab.key as "login" | "register")}
                  className={`rounded-full px-4 py-2 text-sm transition ${
                    active
                      ? "bg-white text-slate-950"
                      : "border border-white/14 text-white/68 hover:bg-white/6"
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          <form onSubmit={onSubmit} className="mt-8 space-y-5">
            <div>
              <label className="mb-2 block text-sm text-white/72">邮箱</label>
              <input
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-full rounded-[1rem] border border-white/12 bg-white/4 px-4 py-3 text-white outline-none transition focus:border-cyan-300/40 focus:bg-white/6"
                placeholder="you@team.com"
              />
            </div>

            {mode === "register" ? (
              <div>
                <label className="mb-2 block text-sm text-white/72">手机号</label>
                <input
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                  className="w-full rounded-[1rem] border border-white/12 bg-white/4 px-4 py-3 text-white outline-none transition focus:border-cyan-300/40 focus:bg-white/6"
                  placeholder="13800000000"
                />
              </div>
            ) : null}

            <div>
              <label className="mb-2 block text-sm text-white/72">密码</label>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full rounded-[1rem] border border-white/12 bg-white/4 px-4 py-3 text-white outline-none transition focus:border-cyan-300/40 focus:bg-white/6"
                placeholder="输入密码"
              />
            </div>

            {error ? (
              <div className="rounded-[1rem] border border-rose-400/25 bg-rose-400/10 px-4 py-3 text-sm text-rose-100">
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={isPending}
              className="display-font w-full rounded-full bg-white px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-100 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isPending ? "处理中..." : mode === "login" ? "进入控制台" : "创建团队并进入"}
            </button>
          </form>
        </div>
      </div>
    </section>
  );
}
