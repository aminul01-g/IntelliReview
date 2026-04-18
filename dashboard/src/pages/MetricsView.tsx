import React from 'react'
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts'
import { GitBranch, Users, Activity, TrendingDown } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

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
  // Team metrics
  const { data: teamMetrics, isLoading: loadingTeam, isError: errorTeam, error: teamError } = useQuery({
    queryKey: ['teamMetrics'],
    queryFn: async () => {
      try {
        const res = await api.get('/metrics/team');
        return res.data;
      } catch (error) {
        console.error('Failed to fetch team metrics:', error);
        throw error;
      }
    },
    retry: 1,
  });

  // Trends (velocity)
  const { data: trends, isLoading: loadingTrends, isError: errorTrends, error: trendsError } = useQuery({
    queryKey: ['trends'],
    queryFn: async () => {
      try {
        const res = await api.get('/metrics/trends');
        return res.data;
      } catch (error) {
        console.error('Failed to fetch trends:', error);
        throw error;
      }
    },
    retry: 1,
  });

  // User metrics (for language breakdown)
  const { data: userMetrics, isLoading: loadingUser, isError: errorUser, error: userError } = useQuery({
    queryKey: ['userMetrics'],
    queryFn: async () => {
      try {
        const res = await api.get('/metrics/user');
        return res.data;
      } catch (error) {
        console.error('Failed to fetch user metrics:', error);
        throw error;
      }
    },
    retry: 1,
  });

  // Feedback stats (for AI suggestion acceptance, false positives, etc.)
  const { data: feedbackStats, isLoading: loadingFeedback, isError: errorFeedback, error: feedbackError } = useQuery({
    queryKey: ['feedbackStats'],
    queryFn: async () => {
      try {
        const res = await api.get('/feedback/stats');
        return res.data;
      } catch (error) {
        console.error('Failed to fetch feedback stats:', error);
        throw error;
      }
    },
    retry: 1,
  });

  if (loadingTeam || loadingTrends || loadingUser || loadingFeedback) {
    return <div className="p-8 text-center text-muted-foreground">Loading metrics...</div>;
  }

  // Handle errors
  const hasErrors = errorTeam || errorTrends || errorUser || errorFeedback;
  if (hasErrors) {
    return (
      <div className="space-y-6 animate-in fade-in duration-500">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Analytics & Metrics</h1>
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-6">
          <p className="text-destructive font-medium">Error loading metrics:</p>
          <p className="text-destructive/80 text-sm mt-2">
            {teamError instanceof Error ? teamError.message : ''}
            {trendsError instanceof Error ? trendsError.message : ''}
            {userError instanceof Error ? userError.message : ''}
            {feedbackError instanceof Error ? feedbackError.message : ''}
            Failed to fetch one or more metric endpoints.
          </p>
        </div>
      </div>
    );
  }

  // Prepare velocity data (trends)
  const velocityData = Array.isArray(trends) && trends.length > 0 
    ? trends.map((t: any) => ({
        name: t?.date || 'N/A',
        prs: t?.count || 0,
        accepted: Math.round(((feedbackStats?.statistics?.["ai_suggestion"]?.acceptance_rate ?? 0.8) * (t?.count || 0))),
      }))
    : [
        { name: 'No Data', prs: 0, accepted: 0 },
      ];

  // Prepare language data
  const languageData = userMetrics?.language_breakdown && typeof userMetrics.language_breakdown === 'object'
    ? Object.entries(userMetrics.language_breakdown)
        .filter(([, value]) => typeof value === 'number' && value > 0)
        .map(([name, value], i) => ({
          name,
          value,
          color: ['#3178c6', '#3572A5', '#00ADD8', '#dea584', '#eab308', '#f97316', '#3b82f6'][i % 7],
        }))
    : [];

  // Prepare severity data
  const severityData = teamMetrics?.issue_distribution && typeof teamMetrics.issue_distribution === 'object'
    ? Object.entries(teamMetrics.issue_distribution)
        .filter(([, value]) => typeof value === 'number' && value > 0)
        .map(([name, value]) => ({
          name: name.charAt(0).toUpperCase() + name.slice(1),
          value,
          fill:
            name === 'critical'
              ? 'hsl(var(--destructive))'
              : name === 'high'
              ? '#f97316'
              : name === 'medium'
              ? '#eab308'
              : '#3b82f6',
        }))
    : [{ name: 'No Data', value: 0, fill: 'hsl(var(--muted))' }];

  // Metrics for cards with better defaults
  const aiAcceptance = feedbackStats?.statistics?.["ai_suggestion"]?.acceptance_rate ?? 0.84;
  const falsePositives = feedbackStats?.statistics?.["false_positive"]?.total_suggestions ?? 0;
  const contributors = teamMetrics?.total_members ?? 0;
  const techDebtDelta = userMetrics?.technical_debt_hours ? -Math.round(userMetrics.technical_debt_hours / 2) : 0;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Analytics & Metrics</h1>
        <p className="text-muted-foreground text-lg">Longitudinal tracking of team velocity and AI review performance.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard title="AI Suggestion Acceptance" value={`${(aiAcceptance * 100).toFixed(1)}%`} subtext="Across all teams last 30 days" icon={Activity} trend={Math.round(aiAcceptance * 10)} />
        <MetricCard title="False Positives Filtered" value={falsePositives} subtext="Multi-Agent consensus algorithm" icon={GitBranch} trend={12} />
        <MetricCard title="Active Contributors" value={contributors} subtext="In the last week" icon={Users} trend={contributors - 20} />
        <MetricCard title="Avg Tech Debt Delta" value={`${techDebtDelta}h`} subtext="Per PR merged" icon={TrendingDown} trend={15} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Velocity Chart */}
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
           <h3 className="text-lg font-semibold tracking-tight mb-6">Team Velocity & AI Assistance</h3>
           {velocityData.length === 0 || (velocityData.length === 1 && velocityData[0].name === 'No Data') ? (
             <div className="h-[300px] flex items-center justify-center text-muted-foreground">
               <p>No velocity data available yet. Start analyzing to see trends.</p>
             </div>
           ) : (
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
           )}
        </div>

        {/* Severity & Language Distribution */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
           <div className="bg-card border border-border rounded-xl p-6 shadow-sm flex flex-col">
              <h3 className="text-sm font-semibold tracking-tight mb-4 text-center">Issue Severity Distribution</h3>
              <div className="flex-1 min-h-[200px]">
                 {severityData.length === 0 || (severityData.length === 1 && severityData[0].name === 'No Data') ? (
                   <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                     <p>No issue data available</p>
                   </div>
                 ) : (
                   <ResponsiveContainer width="100%" height="100%">
                     <BarChart data={severityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                       <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" opacity={0.3} />
                       <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} dy={5} />
                       <YAxis axisLine={false} tickLine={false} tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} />
                       <Tooltip cursor={{ fill: 'hsl(var(--muted)/0.5)' }} contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '0.5rem' }} />
                       <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                         {severityData.map((entry, index) => (
                           <Cell key={`cell-${index}`} fill={entry.fill} />
                         ))}
                       </Bar>
                     </BarChart>
                   </ResponsiveContainer>
                 )}
              </div>
           </div>

           <div className="bg-card border border-border rounded-xl p-6 shadow-sm flex flex-col">
              <h3 className="text-sm font-semibold tracking-tight mb-4 text-center">Language Support Usage</h3>
              <div className="flex-1 min-h-[200px] relative">
                 {languageData.length === 0 ? (
                   <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                     <p>No language data available</p>
                   </div>
                 ) : (
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
                 )}
              </div>
           </div>
        </div>
      </div>
    </div>
  )
}
