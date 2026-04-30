import React, { useState, useMemo } from 'react'
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell,
} from 'recharts'
import * as RechartAll from 'recharts'
const ReferenceLine = (RechartAll as any).ReferenceLine
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import * as LucideIcons from 'lucide-react'

const { Activity, Shield, GitBranch, TrendingUp, Layers, Zap, Target, ArrowRight } = LucideIcons as any

// ── Threshold Sweep Visualization ──────────────────────────────────────

const ThresholdSweepChart = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['thresholdSweep'],
    queryFn: async () => {
      const res = await api.get('/research/threshold-sweep')
      return res.data
    },
  })

  const [selectedThreshold, setSelectedThreshold] = useState(0.85)

  const selectedPoint = useMemo(() => {
    if (!data?.sweep_data) return null
    return data.sweep_data.reduce((closest: any, point: any) =>
      Math.abs(point.threshold - selectedThreshold) < Math.abs(closest.threshold - selectedThreshold)
        ? point : closest
    , data.sweep_data[0])
  }, [data, selectedThreshold])

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
        <div className="h-[400px] flex items-center justify-center text-muted-foreground animate-pulse">
          <Activity className="h-6 w-6 mr-2" /> Loading threshold sweep data...
        </div>
      </div>
    )
  }

  const sweepData = data?.sweep_data || []

  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold tracking-tight flex items-center gap-2">
            <Target className="h-5 w-5 text-primary" />
            Confidence Router — Threshold Sweep
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            Precision / Recall / F1 as a function of the conclusive threshold
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs text-muted-foreground">Optimal F1</div>
          <div className="text-lg font-bold text-primary">
            τ = {data?.optimal_threshold ?? '—'} <span className="text-sm font-normal text-muted-foreground">(F1 = {data?.optimal_f1?.toFixed(4) ?? '—'})</span>
          </div>
        </div>
      </div>

      {/* Interactive slider */}
      <div className="mb-6 p-4 bg-muted/30 rounded-lg border border-border/50">
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-foreground">Threshold: <span className="text-primary font-bold">{selectedThreshold.toFixed(2)}</span></label>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            {selectedPoint && (
              <>
                <span>Precision: <strong className="text-foreground">{(selectedPoint.precision * 100).toFixed(1)}%</strong></span>
                <span>Recall: <strong className="text-foreground">{(selectedPoint.recall * 100).toFixed(1)}%</strong></span>
                <span>F1: <strong className="text-primary">{(selectedPoint.f1 * 100).toFixed(1)}%</strong></span>
                <span>Conclusive: <strong className="text-green-500">{selectedPoint.conclusive_count}</strong></span>
                <span>→ LLM: <strong className="text-orange-400">{selectedPoint.llm_count}</strong></span>
              </>
            )}
          </div>
        </div>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={selectedThreshold}
          onChange={(e) => setSelectedThreshold(parseFloat(e.target.value))}
          className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
        />
        <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
          <span>0.0 (all → LLM)</span>
          <span>1.0 (all conclusive)</span>
        </div>
      </div>

      {/* Chart */}
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={sweepData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" opacity={0.4} />
            <XAxis
              dataKey="threshold"
              axisLine={false}
              tickLine={false}
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
              label={{ value: 'Conclusive Threshold (τ)', position: 'insideBottom', offset: -5, style: { fill: 'hsl(var(--muted-foreground))', fontSize: 11 } }}
            />
            <YAxis
              domain={[0, 1]}
              axisLine={false}
              tickLine={false}
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
              tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            />
            <Tooltip
              contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '0.5rem' }}
              formatter={(value: number, name: string) => [`${(value * 100).toFixed(1)}%`, name]}
              labelFormatter={(label: number) => `Threshold: ${label}`}
            />
            <Legend wrapperStyle={{ paddingTop: '12px', fontSize: '12px' }} />
            <ReferenceLine x={selectedThreshold} stroke="hsl(var(--primary))" strokeDasharray="3 3" strokeWidth={2} />
            <ReferenceLine x={data?.optimal_threshold} stroke="#10b981" strokeDasharray="5 5" strokeWidth={1} />
            <Line type="monotone" name="Precision" dataKey="precision" stroke="#3b82f6" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} />
            <Line type="monotone" name="Recall" dataKey="recall" stroke="#f97316" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} />
            <Line type="monotone" name="F1 Score" dataKey="f1" stroke="#10b981" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4 mt-6">
        <div className="p-3 bg-muted/30 rounded-lg border border-border/50 text-center">
          <p className="text-xs text-muted-foreground">Total Findings</p>
          <p className="text-xl font-bold text-foreground">{data?.total_findings ?? 0}</p>
        </div>
        <div className="p-3 bg-muted/30 rounded-lg border border-border/50 text-center">
          <p className="text-xs text-muted-foreground">Labeled Valid</p>
          <p className="text-xl font-bold text-green-500">{data?.labeled_count ?? 0}</p>
        </div>
        <div className="p-3 bg-muted/30 rounded-lg border border-border/50 text-center">
          <p className="text-xs text-muted-foreground">Cost Savings at τ={selectedThreshold}</p>
          <p className="text-xl font-bold text-primary">
            {selectedPoint ? `$${selectedPoint.simulated_cost.toFixed(2)}` : '—'}
          </p>
        </div>
      </div>
    </div>
  )
}

// ── Ablation Study Chart ───────────────────────────────────────────────

const AblationStudyChart = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['ablationStudy'],
    queryFn: async () => {
      const res = await api.get('/research/ablation-study')
      return res.data
    },
  })

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
        <div className="h-[350px] flex items-center justify-center text-muted-foreground animate-pulse">
          <Layers className="h-6 w-6 mr-2" /> Loading ablation data...
        </div>
      </div>
    )
  }

  const ablationData = data?.ablation_data || []
  const COLORS = ['#6366f1', '#8b5cf6', '#ef4444', '#f97316', '#10b981']

  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold tracking-tight flex items-center gap-2">
            <Layers className="h-5 w-5 text-primary" />
            Ablation Study — Component Contribution
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            Marginal contribution of each pipeline stage to total issue detection
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs text-muted-foreground">Total Issues</div>
          <div className="text-lg font-bold text-foreground">{data?.total_issues ?? 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cumulative bar chart */}
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={ablationData} margin={{ top: 10, right: 10, left: -10, bottom: 40 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" opacity={0.4} />
              <XAxis
                dataKey="component"
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 9 }}
                angle={-20}
                textAnchor="end"
              />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '0.5rem' }}
              />
              <Bar dataKey="cumulative_issues" name="Cumulative Issues" radius={[4, 4, 0, 0]}>
                {ablationData.map((_: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Component details */}
        <div className="space-y-3">
          {ablationData.map((item: any, idx: number) => (
            <div key={idx} className="p-3 rounded-lg border border-border/50 bg-muted/20 hover:bg-muted/30 transition-colors">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                  <span className="text-sm font-medium text-foreground">{item.component}</span>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-muted-foreground">+{item.marginal_issues} issues</span>
                  {item.unique_cwes > 0 && (
                    <span className="text-primary font-medium">{item.unique_cwes} CWEs</span>
                  )}
                  <span className="text-muted-foreground font-mono">conf: {item.avg_confidence}</span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">{item.description}</p>
              {item.examples?.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {item.examples.map((ex: string, i: number) => (
                    <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-muted border border-border/50 text-muted-foreground">
                      {ex}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Pipeline Architecture Flow ─────────────────────────────────────────

const PipelineArchitecture = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['pipelineArchitecture'],
    queryFn: async () => {
      const res = await api.get('/research/pipeline-architecture')
      return res.data
    },
  })

  if (isLoading) return null

  const stages = data?.stages || []
  const typeColors: Record<string, string> = {
    source: 'border-blue-500/30 bg-blue-500/5',
    processor: 'border-purple-500/30 bg-purple-500/5',
    detector: 'border-orange-500/30 bg-orange-500/5',
    decision: 'border-yellow-500/30 bg-yellow-500/5',
    output: 'border-green-500/30 bg-green-500/5',
    learning: 'border-primary/30 bg-primary/5',
  }
  const typeIcons: Record<string, any> = {
    source: LucideIcons.FileCode || Zap,
    processor: Zap,
    detector: Shield,
    decision: GitBranch,
    output: Target,
    learning: TrendingUp,
  }

  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
      <h3 className="text-lg font-semibold tracking-tight flex items-center gap-2 mb-2">
        <Zap className="h-5 w-5 text-primary" />
        Analysis Pipeline Architecture
      </h3>
      <p className="text-sm text-muted-foreground mb-6">
        End-to-end flow from code input to reviewed output with feedback loop
      </p>

      <div className="flex flex-wrap items-start gap-3 justify-center">
        {stages.map((stage: any, idx: number) => {
          const Icon = typeIcons[stage.type] || Zap
          const colorClass = typeColors[stage.type] || 'border-border bg-muted/10'
          return (
            <React.Fragment key={stage.id}>
              <div className={`relative p-4 rounded-xl border-2 ${colorClass} min-w-[140px] max-w-[180px] text-center transition-all hover:scale-105 hover:shadow-md`}>
                <div className="flex justify-center mb-2">
                  <Icon className="h-5 w-5 text-foreground/70" />
                </div>
                <h4 className="text-xs font-bold text-foreground mb-1">{stage.name}</h4>
                <p className="text-[10px] text-muted-foreground leading-tight">{stage.description}</p>
                {stage.threshold && (
                  <div className="mt-2 text-[10px] font-mono text-primary">τ = {stage.threshold}</div>
                )}
                {stage.detectors && (
                  <div className="mt-2 flex flex-wrap gap-0.5 justify-center">
                    {stage.detectors.slice(0, 3).map((d: string, i: number) => (
                      <span key={i} className="text-[8px] px-1 py-0.5 rounded bg-muted/50 border border-border/30 text-muted-foreground">{d}</span>
                    ))}
                  </div>
                )}
              </div>
              {idx < stages.length - 1 && (
                <div className="flex items-center self-center text-muted-foreground/40">
                  <ArrowRight className="h-4 w-4" />
                </div>
              )}
            </React.Fragment>
          )
        })}
      </div>
    </div>
  )
}

// ── Main Research Dashboard ────────────────────────────────────────────

export function ResearchDashboard() {
  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Research Dashboard</h1>
        <p className="text-muted-foreground text-lg mt-1">
          Thesis-grade visualizations of the confidence routing, ablation study, and pipeline architecture.
        </p>
      </div>

      <PipelineArchitecture />
      <ThresholdSweepChart />
      <AblationStudyChart />
    </div>
  )
}
