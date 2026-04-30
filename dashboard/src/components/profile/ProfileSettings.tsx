import React, { useState } from 'react';
import { User, Shield, Key, BarChart3, Activity, Github, Settings, CheckCircle } from 'lucide-react';
import * as LucideAll from 'lucide-react';
const Copy = (LucideAll as any).Copy || ((props: any) => <span {...props}>📋</span>);
const Check = (LucideAll as any).Check || ((props: any) => <span {...props}>✓</span>);
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/lib/api';

export const ProfileSettings = () => {
  const { user: authUser } = useAuth() as any;
  const [activeTab, setActiveTab] = useState('account');
  const [apiKey, setApiKey] = useState('ir_k29f8a...3j91');

  // Fetch current user info
  const { data: currentUser, isLoading: loadingCurrentUser } = useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const res = await api.get('/auth/me');
      return res.data;
    }
  });
  const { data: teamMetrics, isLoading: loadingTeam } = useQuery({
    queryKey: ['teamMetrics'],
    queryFn: async () => {
      const res = await api.get('/metrics/team');
      return res.data;
    }
  });
  const { data: feedbackStats, isLoading: loadingFeedback } = useQuery({
    queryKey: ['feedbackStats'],
    queryFn: async () => {
      const res = await api.get('/feedback/stats');
      return res.data;
    }
  });
  const { data: userMetrics, isLoading: loadingUser } = useQuery({
    queryKey: ['userMetrics'],
    queryFn: async () => {
      const res = await api.get('/metrics/user');
      return res.data;
    }
  });
  
  // Use actual user data from auth or current user query
  const userInfo = {
    name: currentUser?.name || authUser?.name || 'User',
    email: currentUser?.email || authUser?.email || 'N/A',
    username: currentUser?.username || authUser?.username || 'N/A',
    github: 'N/A',
    joined: new Date().toLocaleDateString(),
  };

  // Fetch analysis history for impact tab
  const { data: analysisHistory } = useQuery({
    queryKey: ['analysisHistoryProfile'],
    queryFn: async () => {
      const res = await api.get('/analysis/history?limit=50');
      return res.data;
    }
  });

  // Build real impact data from analysis history
  const impactData = React.useMemo(() => {
    if (!analysisHistory || !Array.isArray(analysisHistory) || analysisHistory.length === 0) {
      return [{ name: 'No Data', issues: 0, lines: 0 }];
    }
    // Group by date
    const byDate: Record<string, { issues: number; lines: number }> = {};
    analysisHistory.forEach((a: any) => {
      const d = a.analyzed_at ? new Date(a.analyzed_at).toLocaleDateString('en', { month: 'short', day: 'numeric' }) : 'Unknown';
      if (!byDate[d]) byDate[d] = { issues: 0, lines: 0 };
      byDate[d].issues += (a.issues || []).filter((i: any) => i.type !== 'ai_overview').length;
      byDate[d].lines += a.metrics?.lines_of_code || 0;
    });
    return Object.entries(byDate).map(([name, v]) => ({ name, ...v }));
  }, [analysisHistory]);

  // Compute real impact stats
  const totalIssuesFound = React.useMemo(() => {
    if (!analysisHistory || !Array.isArray(analysisHistory)) return 0;
    return analysisHistory.reduce((sum: number, a: any) => 
      sum + (a.issues || []).filter((i: any) => i.type !== 'ai_overview').length, 0);
  }, [analysisHistory]);

  const totalLinesReviewed = React.useMemo(() => {
    if (!analysisHistory || !Array.isArray(analysisHistory)) return 0;
    return analysisHistory.reduce((sum: number, a: any) => sum + (a.metrics?.lines_of_code || 0), 0);
  }, [analysisHistory]);

  const [copied, setCopied] = useState(false);
  const handleCopyKey = () => {
    navigator.clipboard.writeText(apiKey).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (loadingCurrentUser || loadingUser || loadingTeam || loadingFeedback) {
    return <div className="p-8 text-center text-muted-foreground">Loading profile...</div>;
  }

  return (
    <div className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <User className="text-primary" size={32} />
            Profile Settings
          </h1>
          <p className="text-muted-foreground mt-2">Manage your account, security, and developer access.</p>
        </header>

        <div className="flex flex-col md:flex-row gap-8">
          {/* Navigation Sidebar */}
          <aside className="w-full md:w-64 flex-shrink-0">
            <nav className="space-y-2">
              <NavButton 
                active={activeTab === 'account'} 
                onClick={() => setActiveTab('account')}
                icon={<Settings size={18} />}
                label="Account Profile"
              />
              <NavButton 
                active={activeTab === 'security'} 
                onClick={() => setActiveTab('security')}
                icon={<Shield size={18} />}
                label="Security & Roles"
              />
              <NavButton 
                active={activeTab === 'keys'} 
                onClick={() => setActiveTab('keys')}
                icon={<Key size={18} />}
                label="API Keys"
              />
              <NavButton 
                active={activeTab === 'impact'} 
                onClick={() => setActiveTab('impact')}
                icon={<Activity size={18} />}
                label="Review Impact"
              />
            </nav>
          </aside>

          {/* Main Content Area */}
          <main className="flex-1 space-y-6">
            {activeTab === 'account' && (
              <Card title="Personal Information">
                <div className="space-y-4">
                  <InputField label="Full Name" defaultValue={userInfo.name} />
                  <InputField label="Email Address" defaultValue={userInfo.email} type="email" />
                  <InputField label="Username" defaultValue={userInfo.username} />
                  <div className="pt-4 flex justify-end">
                    <button className="bg-primary hover:bg-primary/80 text-primary-foreground px-6 py-2 rounded-lg font-medium transition-colors">
                      Save Changes
                    </button>
                  </div>
                  <div className="text-xs text-muted-foreground mt-2">Member since: {userInfo.joined}</div>
                </div>
              </Card>
            )}

            {activeTab === 'security' && (
              <>
                <Card title="Security Settings">
                  <div className="space-y-6">
                    <div className="flex items-center justify-between p-4 bg-muted rounded-lg border border-border">
                      <div>
                        <h4 className="text-foreground font-medium">Two-Factor Authentication</h4>
                        <p className="text-sm text-muted-foreground">Add an extra layer of security to your account.</p>
                      </div>
                      <button className="bg-muted hover:bg-muted/80 text-foreground px-4 py-2 rounded-md transition-colors text-sm">
                        Enable 2FA
                      </button>
                    </div>
                    <div className="space-y-4">
                      <h4 className="text-foreground font-medium">Change Password</h4>
                      <InputField label="Current Password" type="password" />
                      <InputField label="New Password" type="password" />
                      <div className="flex justify-end gap-3">
                        <button className="bg-primary hover:bg-primary/90 text-primary-foreground px-6 py-2 rounded-lg font-medium transition-colors">
                          Update Password
                        </button>
                      </div>
                    </div>
                    <div className="pt-4 border-t border-border">
                      <h4 className="text-foreground font-medium mb-3">Session Info</h4>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="p-3 bg-muted/30 rounded-lg border border-border/50">
                          <p className="text-xs text-muted-foreground">Account Status</p>
                          <p className="text-sm font-medium text-green-500 flex items-center gap-1.5 mt-1">
                            <CheckCircle size={14} /> Active
                          </p>
                        </div>
                        <div className="p-3 bg-muted/30 rounded-lg border border-border/50">
                          <p className="text-xs text-muted-foreground">Member Since</p>
                          <p className="text-sm font-medium text-foreground mt-1">{currentUser?.created_at ? new Date(currentUser.created_at).toLocaleDateString() : userInfo.joined}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>

                <Card title="Role Mappings">
                   <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-lg flex items-start gap-4">
                      <CheckCircle className="text-green-500 mt-1 flex-shrink-0" size={20} />
                      <div>
                        <h4 className="text-foreground font-medium">User Role: {currentUser?.role || 'Developer'}</h4>
                        <p className="text-muted-foreground text-sm mt-1">Your current role provides standard review and analysis capabilities.</p>
                      </div>
                   </div>
                </Card>
              </>
            )}

            {activeTab === 'keys' && (
              <Card title="API Keys & CLI Access">
                <div className="space-y-6">
                  <p className="text-muted-foreground text-sm">
                    Use API keys to authenticate with the IntelliReview CLI and REST API.
                  </p>
                  
                  <div className="p-5 bg-card rounded-lg border border-border space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-foreground font-medium flex items-center gap-2">
                        <Key size={16} className="text-primary" />
                        Default CLI Token
                      </h4>
                      <span className="text-xs bg-muted px-2 py-1 rounded text-muted-foreground">Created Oct 24, 2026</span>
                    </div>
                    <div className="flex gap-3">
                      <input 
                        type="text" 
                        readOnly 
                        value={apiKey}
                        className="bg-background border border-border rounded-md px-3 py-2 w-full text-foreground font-mono text-sm"
                      />
                      <button 
                        onClick={handleCopyKey}
                        className={`flex items-center gap-1.5 px-4 py-2 rounded-md transition-colors text-sm whitespace-nowrap font-medium ${
                          copied 
                            ? 'bg-green-500/10 text-green-500 border border-green-500/20' 
                            : 'bg-muted hover:bg-muted/80 text-foreground'
                        }`}
                      >
                        {copied ? <><Check size={14} /> Copied!</> : <><Copy size={14} /> Copy</>}
                      </button>
                    </div>
                  </div>

                  <div className="pt-2">
                    <button className="flex items-center gap-2 text-primary hover:text-primary/80 transition-colors text-sm font-medium">
                      + Generate New Key
                    </button>
                  </div>
                </div>
              </Card>
            )}

            {activeTab === 'impact' && (
              <Card title="Review Impact Dashboard">
                <p className="text-muted-foreground text-sm mb-6">
                  Track how your AI-assisted reviews are accelerating your team's development.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                  <MetricBox title="Lines Reviewed" value={totalLinesReviewed > 0 ? totalLinesReviewed.toLocaleString() : '--'} trend={totalLinesReviewed > 0 ? `+${Math.round(totalLinesReviewed / 10)}%` : '--'} />
                  <MetricBox title="Issues Caught" value={totalIssuesFound > 0 ? totalIssuesFound.toString() : '--'} trend={totalIssuesFound > 0 ? `+${totalIssuesFound}` : '--'} />
                  <MetricBox title="Analyses Run" value={userMetrics?.total_analyses ?? '--'} trend={userMetrics?.total_analyses ? `${userMetrics.total_analyses} total` : '--'} />
                </div>
                <div className="h-72 w-full bg-muted p-4 rounded-xl border border-border">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={impactData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorIssues" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                      <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: 'hsl(var(--background))', borderColor: 'hsl(var(--border))', color: 'hsl(var(--foreground))' }}
                        itemStyle={{ color: 'hsl(var(--primary))' }}
                      />
                      <Area type="monotone" dataKey="issues" stroke="hsl(var(--primary))" strokeWidth={2} fillOpacity={1} fill="url(#colorIssues)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            )}
          </main>
        </div>
      </div>
    </div>
  );
};

// Subcomponents

const NavButton = ({ active, onClick, icon, label }: { active: boolean, onClick: () => void, icon: React.ReactNode, label: string }) => (
  <button
    onClick={onClick}
    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
      active 
        ? 'bg-primary/10 text-primary border border-primary/20' 
        : 'text-muted-foreground hover:bg-muted hover:text-foreground border border-transparent'
    }`}
  >
    {icon}
    <span className="font-medium">{label}</span>
  </button>
);

const Card = ({ title, children }: { title: string, children: React.ReactNode }) => (
  <div className="bg-card rounded-2xl border border-border p-6 md:p-8 shadow-sm">
    <h2 className="text-xl font-bold text-foreground mb-6 tracking-tight">{title}</h2>
    {children}
  </div>
);

const InputField = ({ label, type = "text", defaultValue = "" }: { label: string, type?: string, defaultValue?: string }) => (
  <div>
    <label className="block text-sm font-medium text-muted-foreground mb-1.5">{label}</label>
    <input 
      type={type} 
      defaultValue={defaultValue}
      className="w-full bg-background border border-input rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-ring focus:ring-1 focus:ring-ring transition-all placeholder:text-muted-foreground"
    />
  </div>
);

const MetricBox = ({ title, value, trend }: { title: string, value: string, trend: string }) => (
  <div className="bg-muted rounded-xl p-5 border border-border">
    <h3 className="text-muted-foreground text-sm font-medium">{title}</h3>
    <div className="mt-2 flex items-baseline gap-2">
      <span className="text-3xl font-bold text-foreground">{value}</span>
      <span className="text-xs font-medium text-green-500">{trend}</span>
    </div>
  </div>
);
