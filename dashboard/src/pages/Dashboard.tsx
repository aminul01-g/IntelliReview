import React from 'react'
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts'
import { Activity, Clock, ShieldAlert, GitMerge } from 'lucide-react'

const healthData = [
  { name: 'Mon', score: 65 },
  { name: 'Tue', score: 70 },
  { name: 'Wed', score: 68 },
  { name: 'Thu', score: 75 },
  { name: 'Fri', score: 82 },
  { name: 'Sat', score: 80 },
  { name: 'Sun', score: 88 },
]

const debtData = [
  { name: 'Mon', hours: 140 },
  { name: 'Tue', hours: 135 },
  { name: 'Wed', hours: 138 },
  { name: 'Thu', hours: 120 },
  { name: 'Fri', hours: 110 },
  { name: 'Sat', hours: 108 },
  { name: 'Sun', hours: 104 },
]

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
  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight mb-2 text-foreground">Command Center</h1>
        <p className="text-muted-foreground text-lg">High-level telemetry overview and system health trajectory.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
         <MetricCard 
           title="Health Score" 
           value="88/100" 
           icon={Activity} 
           data={healthData} 
           dataKey="score" 
           color="hsl(var(--primary))" 
           trend={12} 
         />
         <MetricCard 
           title="Tech Debt Hours" 
           value="104h" 
           icon={Clock} 
           data={debtData} 
           dataKey="hours" 
           color="hsl(var(--destructive))" 
           trend={-25} 
         />
         <div className="bg-card border border-border rounded-xl p-5 flex flex-col gap-4 shadow-sm h-36 justify-between hover:shadow-md transition-shadow group">
            <div className="flex items-center gap-2 text-muted-foreground font-medium text-sm tracking-wide max-w-fit bg-muted/30 px-3 py-1.5 rounded-full border border-border/50 group-hover:bg-muted/50 transition-colors">
               <ShieldAlert className="h-4 w-4" />
               Critical Findings
            </div>
            <div className="text-4xl font-bold tracking-tight text-foreground flex items-center justify-between">
               0
               <span className="text-sm font-normal text-muted-foreground tracking-normal block ml-2 text-right">Resolved across <br/> 14 active projects</span>
            </div>
         </div>
         <div className="bg-card border border-border rounded-xl p-5 flex flex-col gap-4 shadow-sm h-36 justify-between hover:shadow-md transition-shadow group">
            <div className="flex items-center gap-2 text-muted-foreground font-medium text-sm tracking-wide max-w-fit bg-muted/30 px-3 py-1.5 rounded-full border border-border/50 group-hover:bg-muted/50 transition-colors">
               <GitMerge className="h-4 w-4" />
               PRs Scanned
            </div>
            <div className="text-4xl font-bold tracking-tight text-foreground flex items-center justify-between">
               1,204
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
             False Positive Reduction Trajectory
           </h3>
           <div className="h-[300px] w-full flex items-center justify-center border-2 border-dashed border-border/50 rounded-lg bg-muted/5 text-muted-foreground">
              [Telemetry Moving Averages Graph Render]
           </div>
        </div>
        <div className="border border-border rounded-xl bg-card p-6 shadow-sm hover:shadow-md transition-shadow">
           <h3 className="font-semibold text-lg mb-6 tracking-tight flex items-center gap-3">
             <Clock className="h-5 w-5 text-primary" />
             Rules Firing Frequency
           </h3>
           <div className="h-[300px] w-full flex items-center justify-center border-2 border-dashed border-border/50 rounded-lg bg-muted/5 text-muted-foreground">
              [Radar Chart Render]
           </div>
        </div>
      </div>
    </div>
  )
}
