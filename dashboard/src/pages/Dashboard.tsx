import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts'
import { Activity, Clock, ShieldAlert, GitMerge } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { OnboardingWizard } from '@/components/ui/OnboardingWizard'

const MetricCard = ({ title, value, icon: Icon, data, dataKey, color, trend }: any) => (
  <div className="bg-card border border-border rounded-xl p-5 flex flex-col gap-4 shadow-sm hover:shadow-md transition-shadow group">
     <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-muted-foreground font-medium text-sm tracking-wide bg-muted/30 px-3 py-1.5 rounded-full border border-border/50 group-hover:bg-muted/50 transition-colors">
           <Icon className="h-4 w-4" />
           {title}
        </div>
        <div className={`text-xs font-bold ${trend > 0 ? 'text-green-500 bg-green-500/10' : 'text-destructive bg-destructive/10'} px-2 py-0.5 rounded-md shrink-0`}>
           {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}%
        </div>
     </div>
     
     <div className="flex items-end justify-between gap-4 mt-2">
        <div className="text-4xl font-bold tracking-tight text-foreground">
          {value}
        </div>
        <div className="h-16 w-32 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <Line 
                type="monotone" 
                dataKey={dataKey} 
                stroke={color} 
                strokeWidth={3} 
                dot={false}
                isAnimationActive={true}
              />
              <Tooltip 
                contentStyle={{ backgroundColor: 'hsl(var(--background))', borderColor: 'hsl(var(--border))', borderRadius: '0.5rem', fontSize: '12px' }}
                itemStyle={{ color: 'hsl(var(--foreground))' }}
                cursor={{ stroke: 'hsl(var(--border))', strokeWidth: 1, strokeDasharray: '4 4' }}
                labelStyle={{ display: 'none' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
     </div>
  </div>
)

export function Dashboard() {
  // User metrics
  const { data: userMetrics, isLoading: loadingUser } = useQuery({
    queryKey: ['userMetrics'],
    queryFn: async () => {
      const res = await api.get('/metrics/user');
      return res.data;
    }
  });

  // Team metrics
  const { data: teamMetrics, isLoading: loadingTeam } = useQuery({
    queryKey: ['teamMetrics'],
    queryFn: async () => {
      const res = await api.get('/metrics/team');
      return res.data;
    }
  });

  // Trends (for health/velocity chart)
  const { data: trends, isLoading: loadingTrends } = useQuery({
    queryKey: ['trends'],
    queryFn: async () => {
      const res = await api.get('/metrics/trends');
      return res.data;
    }
  });

  // Loading state
  const navigate = useNavigate()
  const [onboardingDismissed, setOnboardingDismissed] = useState(() => {
    try { return localStorage.getItem('ir_onboarding_done') === '1' } catch { return false }
  })

  const handleDismissOnboarding = () => {
    setOnboardingDismissed(true)
    try { localStorage.setItem('ir_onboarding_done', '1') } catch {}
  }

  if (loadingUser || loadingTeam || loadingTrends) {
    return <div className="p-8 text-center text-muted-foreground">Loading dashboard metrics...</div>;
  }

  // Prepare chart data from real API responses
  const healthData = (trends || []).map((t: any) => ({ name: t.date, score: t.count }));
  const debtData = [
    { name: 'This Week', hours: userMetrics?.technical_debt_hours ?? 0 },
  ];

  // Compute meaningful health score from available data
  const totalAnalyses = userMetrics?.total_analyses ?? 0;
  const healthScore = totalAnalyses > 0
    ? Math.min(100, 50 + totalAnalyses * 5)
    : null;

  const showOnboarding = totalAnalyses === 0 && !onboardingDismissed

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight mb-2 text-foreground">Command Center</h1>
        <p className="text-muted-foreground text-lg">High-level telemetry overview and system health trajectory.</p>
      </div>

      {showOnboarding && (
        <OnboardingWizard
          onDismiss={handleDismissOnboarding}
          onTryReview={() => {
            handleDismissOnboarding()
            navigate('/review')
          }}
        />
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
         <MetricCard 
           title="Health Score" 
           value={healthScore !== null ? `${healthScore}/100` : '--/100'}
           icon={Activity} 
           data={healthData} 
           dataKey="score" 
           color="hsl(var(--primary))" 
           trend={totalAnalyses > 0 ? Math.round(totalAnalyses * 2) : 0} 
         />
         <MetricCard 
           title="Tech Debt Hours" 
           value={userMetrics ? `${userMetrics.technical_debt_hours ?? 0}h` : '--'}
           icon={Clock} 
           data={debtData} 
           dataKey="hours" 
           color="hsl(var(--destructive))" 
           trend={userMetrics?.technical_debt_hours ? -Math.round(userMetrics.technical_debt_hours / 2) : 0} 
         />
         <div className="bg-card border border-border rounded-xl p-5 flex flex-col gap-4 shadow-sm h-36 justify-between hover:shadow-md transition-shadow group">
            <div className="flex items-center gap-2 text-muted-foreground font-medium text-sm tracking-wide max-w-fit bg-muted/30 px-3 py-1.5 rounded-full border border-border/50 group-hover:bg-muted/50 transition-colors">
               <ShieldAlert className="h-4 w-4" />
               Critical Findings
            </div>
            <div className="text-4xl font-bold tracking-tight text-foreground flex items-center justify-between">
               {teamMetrics?.issue_distribution?.critical ?? 0}
               <span className="text-sm font-normal text-muted-foreground tracking-normal block ml-2 text-right">Resolved across <br/> {teamMetrics?.total_members ?? 1} active projects</span>
            </div>
         </div>
         <div className="bg-card border border-border rounded-xl p-5 flex flex-col gap-4 shadow-sm h-36 justify-between hover:shadow-md transition-shadow group">
            <div className="flex items-center gap-2 text-muted-foreground font-medium text-sm tracking-wide max-w-fit bg-muted/30 px-3 py-1.5 rounded-full border border-border/50 group-hover:bg-muted/50 transition-colors">
               <GitMerge className="h-4 w-4" />
               PRs Scanned
            </div>
            <div className="text-4xl font-bold tracking-tight text-foreground flex items-center justify-between">
               {userMetrics?.total_analyses ?? 0}
               <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center">
                 <GitMerge className="h-4 w-4 text-primary" />
               </div>
            </div>
         </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 border border-border rounded-xl bg-card p-6 shadow-sm hover:shadow-md transition-shadow">
           <h3 className="font-semibold text-lg mb-6 tracking-tight flex items-center gap-3">
             <Activity className="h-5 w-5 text-primary" />
             Analysis Activity
           </h3>
           {healthData.length > 0 ? (
             <div className="h-[300px] w-full">
               <ResponsiveContainer width="100%" height="100%">
                 <LineChart data={healthData}>
                   <Line 
                     type="monotone" 
                     dataKey="score" 
                     stroke="hsl(var(--primary))" 
                     strokeWidth={3} 
                     dot={{ r: 4, strokeWidth: 2 }}
                     activeDot={{ r: 6 }}
                     isAnimationActive={true}
                   />
                   <Tooltip 
                     contentStyle={{ backgroundColor: 'hsl(var(--background))', borderColor: 'hsl(var(--border))', borderRadius: '0.5rem', fontSize: '12px' }}
                     itemStyle={{ color: 'hsl(var(--foreground))' }}
                   />
                 </LineChart>
               </ResponsiveContainer>
             </div>
           ) : (
             <div className="h-[300px] w-full flex items-center justify-center border-2 border-dashed border-border/50 rounded-lg bg-muted/5 text-muted-foreground">
                Upload a project or run an analysis to see activity trends.
             </div>
           )}
        </div>
        <div className="border border-border rounded-xl bg-card p-6 shadow-sm hover:shadow-md transition-shadow">
           <h3 className="font-semibold text-lg mb-6 tracking-tight flex items-center gap-3">
             <Clock className="h-5 w-5 text-primary" />
             Recent Scans
           </h3>
           {totalAnalyses > 0 ? (
             <div className="space-y-3">
               <div className="text-center text-5xl font-bold text-primary">{totalAnalyses}</div>
               <div className="text-center text-muted-foreground text-sm">Total analyses run</div>
               <div className="pt-4 text-center">
                 <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-medium">
                   <Activity className="h-4 w-4" /> Active
                 </div>
               </div>
             </div>
           ) : (
             <div className="h-[300px] w-full flex items-center justify-center border-2 border-dashed border-border/50 rounded-lg bg-muted/5 text-muted-foreground text-sm text-center px-4">
                No scans yet. Try the Review Engine to analyze your first code snippet.
             </div>
           )}
        </div>
      </div>
    </div>
  )
}
