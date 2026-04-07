"use client";

import { useEffect, useState } from "react";

import { ConsoleShell } from "@/components/console-shell";
import { fetchOffers, fetchProviderHealth } from "@/lib/api";
import type { ProviderHealth, ProviderOffer } from "@/lib/mock";

export default function AdminProvidersPage() {
  const [health, setHealth] = useState<ProviderHealth[]>([]);
  const [offers, setOffers] = useState<ProviderOffer[]>([]);

  useEffect(() => {
    void Promise.all([fetchProviderHealth(), fetchOffers()]).then(([healthRows, offerRows]) => {
      setHealth(healthRows);
      setOffers(offerRows);
    });
  }, []);

  return (
    <ConsoleShell current="/admin/providers" eyebrow="Supply Plane" title="资源池与健康度">
      <div className="grid gap-6 xl:grid-cols-[0.88fr_1.12fr]">
        <section className="glass-panel rounded-[1.75rem] p-6">
          <h3 className="text-lg font-semibold text-white">Provider 健康度</h3>
          <div className="mt-5 space-y-3">
            {health.map((provider) => (
              <div key={provider.provider} className="rounded-[1.2rem] border border-white/8 bg-white/3 px-4 py-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-white">{provider.provider}</span>
                  <span className="text-sm text-white/58">{provider.offerCount} offers</span>
                </div>
                <p className="mt-2 text-sm text-white/58">
                  平均价 ${provider.averagePricePerHour.toFixed(2)} /h · 可靠性 {provider.averageReliability.toFixed(2)}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="glass-panel rounded-[1.75rem] p-6">
          <h3 className="text-lg font-semibold text-white">当前 offer 列表</h3>
          <div className="mt-5 overflow-x-auto">
            <table className="min-w-full text-left text-sm text-white/72">
              <thead className="text-xs uppercase tracking-[0.18em] text-white/38">
                <tr>
                  <th className="pb-3">Provider</th>
                  <th className="pb-3">GPU</th>
                  <th className="pb-3">区域</th>
                  <th className="pb-3">价格</th>
                  <th className="pb-3">可靠性</th>
                  <th className="pb-3">成功率</th>
                </tr>
              </thead>
              <tbody>
                {offers.map((offer) => (
                  <tr key={`${offer.provider}-${offer.gpuType}`} className="border-t border-white/8">
                    <td className="py-4">{offer.provider}</td>
                    <td className="py-4">{offer.gpuType}</td>
                    <td className="py-4">{offer.region ?? "--"}</td>
                    <td className="py-4">${offer.pricePerHour.toFixed(2)}</td>
                    <td className="py-4">{offer.reliabilityScore.toFixed(2)}</td>
                    <td className="py-4">{(offer.successRate * 100).toFixed(0)}%</td>
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
