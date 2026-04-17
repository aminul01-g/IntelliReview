import React from 'react'
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts'
import { GitBranch, Users, Activity, TrendingDown } from 'lucide-react'

const velocityData = [
  { name: 'Week 1', prs: 14, issues: 24, accepted: 20 },
  { name: 'Week 2', prs: 22, issues: 18, accepted: 16 },
  { name: 'Week 3', prs: 19, issues: 30, accepted: 28 },
  { name: 'Week 4', prs: 28, issues: 20, accepted: 19 },
  { name: 'Week 5', prs: 35, issues: 15, accepted: 14 },
]

const languageData = [
  { name: 'TypeScript', value: 45, color: '#3178c6' },
  { name: 'Python', value: 30, color: '#3572A5' },
  { name: 'Go', value: 15, color: '#00ADD8' },
  { name: 'Rust', value: 10, color: '#dea584' },
]

const severityData = [
  { name: 'Critical', value: 12, fill: 'hsl(var(--destructive))' },
  { name: 'High', value: 34, fill: '#f97316' },
  { name: 'Medium', value: 85, fill: '#eab308' },
  { name: 'Low', value: 140, fill: '#3b82f6' },
]

const MetricCard = ({ title, value, subtext, icon: Icon, trend }: any) => (
  <div className="bg-card border border-border rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow group">
     <div className="flex items-center justify-between mb-4">
        <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary/20 transition-colors">
          <Icon className="h-5 w-5" />
        </div>
        <div className={`px-2 py-1 rounded-md text-xs font-semibold ${trend > 0 ? 'bg-green-500/10 text-green-500' : 'bg-destructive/10 text-destructive'}`}>
          {trend > 0 ? '+' : ''}{trend}%
        </div>
     </div>
     <h3 className="text-3xl font-bold tracking-tight text-foreground">{value}</h3>
     <p className="text-sm text-muted-foreground font-medium mt-1">{title}</p>
     <p className="text-xs text-muted-foreground/70 mt-3">{subtext}</p>
  </div>
)

export function MetricsView() {
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Analytics & Metrics</h1>
        <p className="text-muted-foreground text-lg">Longitudinal tracking of team velocity and AI review performance.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard title="AI Suggestion Acceptance" value="84.2%" subtext="Across all teams last 30 days" icon={Activity} trend={4.5} />
        <MetricCard title="False Positives Filtered" value="1,240" subtext="Multi-Agent consensus algorithm" icon={GitBranch} trend={12} />
        <MetricCard title="Active Contributors" value="28" subtext="In the last week" icon={Users} trend={-2} />
        <MetricCard title="Avg Tech Debt Delta" value="-12h" subtext="Per PR merged" icon={TrendingDown} trend={15} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Velocity Chart */}
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
           <h3 className="text-lg font-semibold tracking-tight mb-6">Team Velocity & AI Assistance</h3>
           <div className="h-[300px] w-full">
             <ResponsiveContainer width="100%" height="100%">
               <LineChart data={velocityData}>
                 <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" opacity={0.5} />
                 <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }} dy={10} />
                 <YAxis axisLine={false} tickLine={false} tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }} dx={-10} />
                 <Tooltip 
                   contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '0.5rem', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                   itemStyle={{ fontSize: '13px' }}
                   labelStyle={{ color: 'hsl(var(--foreground))', fontWeight: 'bold', marginBottom: '4px' }}
                 />
                 <Legend wrapperStyle={{ paddingTop: '20px', fontSize: '12px' }} />
                 <Line type="monotone" name="Merged PRs" dataKey="prs" stroke="hsl(var(--primary))" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
                 <Line type="monotone" name="AI Suggestions Accepted" dataKey="accepted" stroke="#10b981" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} />
               </LineChart>
             </ResponsiveContainer>
           </div>
        </div>

        {/* Severity & Language Distribution */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
           <div className="bg-card border border-border rounded-xl p-6 shadow-sm flex flex-col">
              <h3 className="text-sm font-semibold tracking-tight mb-4 text-center">Issue Severity Distribution</h3>
              <div className="flex-1 min-h-[200px]">
                 <ResponsiveContainer width="100%" height="100%">
                   <BarChart data={severityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                     <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" opacity={0.3} />
                     <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} dy={5} />
                     <YAxis axisLine={false} tickLine={false} tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} />
                     <Tooltip cursor={{ fill: 'hsl(var(--muted)/0.5)' }} contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '0.5rem' }} />
                     <Bar dataKey="value" radius={[4, 4, 0, 0]} />
                   </BarChart>
                 </ResponsiveContainer>
              </div>
           </div>

           <div className="bg-card border border-border rounded-xl p-6 shadow-sm flex flex-col">
              <h3 className="text-sm font-semibold tracking-tight mb-4 text-center">Language Support Usage</h3>
              <div className="flex-1 min-h-[200px] relative">
                 <ResponsiveContainer width="100%" height="100%">
                   <PieChart>
                     <Pie
                       data={languageData}
                       cx="50%"
                       cy="50%"
                       innerRadius={40}
                       outerRadius={70}
                       paddingAngle={5}
                       dataKey="value"
                       stroke="none"
                     >
                       {languageData.map((entry, index) => (
                         <Cell key={`cell-${index}`} fill={entry.color} />
                       ))}
                     </Pie>
                     <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '0.5rem' }} />
                   </PieChart>
                 </ResponsiveContainer>
              </div>
           </div>
        </div>
      </div>
    </div>
  )
}
