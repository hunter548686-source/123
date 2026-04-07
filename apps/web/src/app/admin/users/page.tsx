"use client";

import { useEffect, useState } from "react";

import { ConsoleShell } from "@/components/console-shell";
import { fetchAdminUsers } from "@/lib/api";
import type { AdminUserOverview } from "@/lib/mock";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUserOverview[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    void fetchAdminUsers()
      .then(setUsers)
      .catch((err) => {
        setError(err instanceof Error ? err.message : "加载用户列表失败。");
      });
  }, []);

  return (
    <ConsoleShell current="/admin/users" eyebrow="Users Console" title="用户与权限">
      <section className="glass-panel rounded-[1.75rem] p-6">
        {error ? (
          <div className="mb-4 rounded-[1rem] border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-100">
            {error}
          </div>
        ) : null}
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm text-white/72">
            <thead className="text-xs uppercase tracking-[0.18em] text-white/38">
              <tr>
                <th className="pb-3">用户</th>
                <th className="pb-3">角色</th>
                <th className="pb-3">状态</th>
                <th className="pb-3">钱包</th>
                <th className="pb-3">任务概览</th>
                <th className="pb-3">注册时间</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-t border-white/8">
                  <td className="py-4">
                    <p className="font-medium text-white">#{user.id}</p>
                    <p className="mt-1 text-xs text-white/52">{user.email}</p>
                  </td>
                  <td className="py-4 uppercase text-cyan-100/80">{user.role}</td>
                  <td className="py-4">{user.status}</td>
                  <td className="py-4">
                    <p>可用 {user.walletBalance.toFixed(2)}</p>
                    <p className="text-xs text-white/52">
                      冻结 {user.frozenBalance.toFixed(2)}
                    </p>
                  </td>
                  <td className="py-4">
                    <p>total {user.totalTasks} / running {user.runningTasks}</p>
                    <p className="text-xs text-white/52">
                      completed {user.completedTasks} / failed {user.failedTasks}
                    </p>
                  </td>
                  <td className="py-4 text-white/52">
                    {new Date(user.createdAt).toLocaleString()}
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
