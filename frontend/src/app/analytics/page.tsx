"use client"

import { useEffect, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"

type PRPoint = { precision: number; recall: number }

type StrategyResult = {
  name: string
  n_sessions: number
  map: number | null
  avg_p_at_k: number | null
  avg_dcg: number | null
  avg_dcg_at_k: number[]
  pr_curve: PRPoint[]
}

type AnalyticsData = {
  strategies: StrategyResult[]
  overall: { map: number; avg_p_at_k: number; n_sessions: number }
}

const STRATEGY_COLORS: Record<string, string> = {
  weighted_vector: "#3b82f6",
  gemini: "#a855f7",
  fuzzy_cluster: "#22c55e",
  k_nearest: "#f97316",
}

const STRATEGY_LABELS: Record<string, string> = {
  weighted_vector: "Weighted Vector",
  gemini: "Gemini",
  fuzzy_cluster: "Fuzzy Cluster",
  k_nearest: "K-Nearest",
}

function MetricBars({
  strategies,
  getValue,
  label,
  maxValue,
}: {
  strategies: StrategyResult[]
  getValue: (s: StrategyResult) => number | null
  label: string
  maxValue?: number
}) {
  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{label}</p>
      {strategies.map((s) => {
        const value = getValue(s)
        const color = STRATEGY_COLORS[s.name] ?? "#6b7280"
        const scale = maxValue != null && maxValue > 0 ? maxValue : 1
        return (
          <div key={s.name} className="flex items-center gap-3">
            <div className="w-32 text-sm text-right text-muted-foreground shrink-0">
              {STRATEGY_LABELS[s.name] ?? s.name}
            </div>
            <div className="flex-1 h-5 bg-muted rounded-full overflow-hidden relative">
              {value !== null ? (
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${(value / scale) * 100}%`, backgroundColor: color }}
                />
              ) : (
                <span className="absolute inset-0 flex items-center px-3 text-xs text-muted-foreground">
                  No data yet
                </span>
              )}
            </div>
            <div className="w-12 text-sm font-mono text-right shrink-0">
              {value !== null ? value.toFixed(3) : "—"}
            </div>
            <div className="w-20 text-xs text-muted-foreground shrink-0 text-right">
              {s.n_sessions > 0 ? `n=${s.n_sessions}` : ""}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function PRCurveChart({ strategies }: { strategies: StrategyResult[] }) {
  const svgW = 500
  const svgH = 300
  const pad = { top: 20, right: 20, bottom: 48, left: 52 }
  const chartW = svgW - pad.left - pad.right
  const chartH = svgH - pad.top - pad.bottom

  const toX = (recall: number) => pad.left + recall * chartW
  const toY = (precision: number) => pad.top + (1 - precision) * chartH
  const ticks = [0, 0.25, 0.5, 0.75, 1.0]
  const active = strategies.filter((s) => s.n_sessions > 0 && s.pr_curve.length > 0)

  return (
    <svg viewBox={`0 0 ${svgW} ${svgH}`} className="w-full">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={toX(0)} y1={toY(t)} x2={toX(1)} y2={toY(t)} stroke="#e5e7eb" strokeWidth={1} />
          <line x1={toX(t)} y1={toY(1)} x2={toX(t)} y2={toY(0)} stroke="#e5e7eb" strokeWidth={1} />
          <text x={toX(t)} y={toY(0) + 16} textAnchor="middle" fontSize={10} fill="#9ca3af">
            {t.toFixed(2)}
          </text>
          <text x={toX(0) - 8} y={toY(t) + 4} textAnchor="end" fontSize={10} fill="#9ca3af">
            {t.toFixed(2)}
          </text>
        </g>
      ))}
      <line x1={toX(0)} y1={toY(0)} x2={toX(1)} y2={toY(0)} stroke="#6b7280" strokeWidth={1.5} />
      <line x1={toX(0)} y1={toY(1)} x2={toX(0)} y2={toY(0)} stroke="#6b7280" strokeWidth={1.5} />
      <text x={svgW / 2} y={svgH - 6} textAnchor="middle" fontSize={11} fill="#6b7280">
        Recall
      </text>
      <text
        x={12}
        y={svgH / 2}
        textAnchor="middle"
        fontSize={11}
        fill="#6b7280"
        transform={`rotate(-90, 12, ${svgH / 2})`}
      >
        Precision
      </text>

      {active.map((strategy) => {
        const color = STRATEGY_COLORS[strategy.name] ?? "#6b7280"
        const d = strategy.pr_curve
          .map((p, i) => `${i === 0 ? "M" : "L"}${toX(p.recall).toFixed(1)},${toY(p.precision).toFixed(1)}`)
          .join(" ")
        return (
          <g key={strategy.name}>
            <path d={d} fill="none" stroke={color} strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
            {strategy.pr_curve.map((pt, i) => (
              <circle key={i} cx={toX(pt.recall)} cy={toY(pt.precision)} r={3} fill={color} />
            ))}
          </g>
        )
      })}
    </svg>
  )
}

function DCGAtKChart({ strategies }: { strategies: StrategyResult[] }) {
  const svgW = 500
  const svgH = 300
  const pad = { top: 20, right: 20, bottom: 48, left: 52 }
  const chartW = svgW - pad.left - pad.right
  const chartH = svgH - pad.top - pad.bottom

  const active = strategies.filter((s) => s.n_sessions > 0 && s.avg_dcg_at_k?.length > 0)
  const maxK = Math.max(...active.map((s) => s.avg_dcg_at_k.length), 1)
  const maxDCG = Math.max(...active.flatMap((s) => s.avg_dcg_at_k), 1)
  const yTicks = [0, 0.25, 0.5, 0.75, 1.0].map((t) => t * maxDCG)

  const toX = (k: number) => pad.left + (k / (maxK - 1)) * chartW
  const toY = (dcg: number) => pad.top + (1 - dcg / maxDCG) * chartH

  return (
    <svg viewBox={`0 0 ${svgW} ${svgH}`} className="w-full">
      {yTicks.map((t) => (
        <g key={t}>
          <line x1={pad.left} y1={toY(t)} x2={pad.left + chartW} y2={toY(t)} stroke="#e5e7eb" strokeWidth={1} />
          <text x={pad.left - 8} y={toY(t) + 4} textAnchor="end" fontSize={10} fill="#9ca3af">
            {t.toFixed(1)}
          </text>
        </g>
      ))}
      {Array.from({ length: maxK }, (_, k) => (
        <g key={k}>
          <line x1={toX(k)} y1={pad.top} x2={toX(k)} y2={pad.top + chartH} stroke="#e5e7eb" strokeWidth={1} />
          <text x={toX(k)} y={pad.top + chartH + 16} textAnchor="middle" fontSize={10} fill="#9ca3af">
            {k + 1}
          </text>
        </g>
      ))}
      <line x1={pad.left} y1={pad.top + chartH} x2={pad.left + chartW} y2={pad.top + chartH} stroke="#6b7280" strokeWidth={1.5} />
      <line x1={pad.left} y1={pad.top} x2={pad.left} y2={pad.top + chartH} stroke="#6b7280" strokeWidth={1.5} />
      <text x={svgW / 2} y={svgH - 6} textAnchor="middle" fontSize={11} fill="#6b7280">
        Rank position k
      </text>
      <text x={12} y={svgH / 2} textAnchor="middle" fontSize={11} fill="#6b7280" transform={`rotate(-90, 12, ${svgH / 2})`}>
        DCG
      </text>
      {active.map((strategy) => {
        const color = STRATEGY_COLORS[strategy.name] ?? "#6b7280"
        const d = strategy.avg_dcg_at_k
          .map((v, i) => `${i === 0 ? "M" : "L"}${toX(i).toFixed(1)},${toY(v).toFixed(1)}`)
          .join(" ")
        return (
          <g key={strategy.name}>
            <path d={d} fill="none" stroke={color} strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
            {strategy.avg_dcg_at_k.map((v, i) => (
              <circle key={i} cx={toX(i)} cy={toY(v)} r={3} fill={color} />
            ))}
          </g>
        )
      })}
    </svg>
  )
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card>
      <CardContent className="p-5">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-3xl font-bold mt-1">{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      </CardContent>
    </Card>
  )
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    fetch(`${apiUrl}/api/analytics`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load analytics")
        return res.json() as Promise<AnalyticsData>
      })
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Unknown error"))
  }, [])

  if (error) {
    return (
      <div className="max-w-xl mx-auto p-6 pt-20 text-center">
        <p className="text-destructive text-sm">{error}</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="max-w-xl mx-auto p-6 pt-20 text-center">
        <p className="text-muted-foreground text-sm">Loading analytics…</p>
      </div>
    )
  }

  const { strategies, overall } = data

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Analytics</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Recommender comparison across {overall.n_sessions} session
          {overall.n_sessions !== 1 ? "s" : ""}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Sessions" value={String(overall.n_sessions)} />
        <StatCard label="MAP" value={overall.map.toFixed(3)} sub="Mean Average Precision" />
        <StatCard label="Avg Precision@k" value={overall.avg_p_at_k.toFixed(3)} sub="Across all recommenders" />
      </div>

      <Card>
        <CardContent className="p-6 space-y-6">
          <MetricBars strategies={strategies} getValue={(s) => s.map} label="MAP — Mean Average Precision" />
          <div className="border-t" />
          <MetricBars strategies={strategies} getValue={(s) => s.avg_p_at_k} label="Precision@k" />
          <div className="border-t" />
          <MetricBars
            strategies={strategies}
            getValue={(s) => s.avg_dcg}
            label="DCG — Discounted Cumulative Gain"
            maxValue={Math.max(...strategies.map((s) => s.avg_dcg ?? 0))}
          />
        </CardContent>
      </Card>

      <div className="space-y-2">
        <h2 className="text-base font-semibold">DCG@k — Cumulative Gain by Rank</h2>
        <p className="text-xs text-muted-foreground">
          Cumulative DCG at each rank position · averaged across sessions per recommender · steeper = better early ranking
        </p>
        <Card>
          <CardContent className="p-5 space-y-4">
            <DCGAtKChart strategies={strategies} />
            <div className="flex flex-wrap gap-4 justify-center">
              {strategies
                .filter((s) => s.n_sessions > 0)
                .map((s) => (
                  <span key={s.name} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <span
                      className="inline-block size-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: STRATEGY_COLORS[s.name] ?? "#6b7280" }}
                    />
                    {STRATEGY_LABELS[s.name] ?? s.name}
                  </span>
                ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-2">
        <h2 className="text-base font-semibold">Precision-Recall Curve</h2>
        <p className="text-xs text-muted-foreground">
          11-point interpolated · averaged across sessions per recommender · relevant = rating ≥ 3
        </p>
        <Card>
          <CardContent className="p-5 space-y-4">
            <PRCurveChart strategies={strategies} />
            <div className="flex flex-wrap gap-4 justify-center">
              {strategies
                .filter((s) => s.n_sessions > 0)
                .map((s) => (
                  <span key={s.name} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <span
                      className="inline-block size-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: STRATEGY_COLORS[s.name] ?? "#6b7280" }}
                    />
                    {STRATEGY_LABELS[s.name] ?? s.name}
                  </span>
                ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
