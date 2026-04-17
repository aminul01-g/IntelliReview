import React, { useState } from 'react';
import { User, Shield, Key, BarChart3, Activity, Github, Settings, CheckCircle } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const mockImpactData = [
  { name: 'Mon', issues: 4, lines: 120 },
  { name: 'Tue', issues: 7, lines: 300 },
  { name: 'Wed', issues: 2, lines: 50 },
  { name: 'Thu', issues: 10, lines: 450 },
  { name: 'Fri', issues: 5, lines: 180 },
  { name: 'Sat', issues: 1, lines: 20 },
  { name: 'Sun', issues: 0, lines: 0 },
];

export const ProfileSettings = () => {
  const [activeTab, setActiveTab] = useState('account');
  const [apiKey, setApiKey] = useState('ir_k29f8a...3j91');

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <User className="text-blue-500" size={32} />
            Profile Settings
          </h1>
          <p className="text-slate-400 mt-2">Manage your account, security, and developer access.</p>
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
                  <InputField label="Full Name" defaultValue="Alex Developer" />
                  <InputField label="Email Address" defaultValue="alex@example.com" type="email" />
                  <InputField label="GitHub Username" defaultValue="alexdev101" />
                  <div className="pt-4 flex justify-end">
                    <button className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors">
                      Save Changes
                    </button>
                  </div>
                </div>
              </Card>
            )}

            {activeTab === 'security' && (
              <>
                <Card title="Security Settings">
                  <div className="space-y-6">
                    <div className="flex items-center justify-between p-4 bg-slate-900 rounded-lg border border-slate-800">
                      <div>
                        <h4 className="text-white font-medium">Two-Factor Authentication</h4>
                        <p className="text-sm text-slate-400">Add an extra layer of security to your account.</p>
                      </div>
                      <button className="bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-md transition-colors text-sm">
                        Enable 2FA
                      </button>
                    </div>
                    <div className="space-y-4">
                      <h4 className="text-white font-medium">Change Password</h4>
                      <InputField label="Current Password" type="password" />
                      <InputField label="New Password" type="password" />
                      <div className="flex justify-end">
                        <button className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors">
                          Update Password
                        </button>
                      </div>
                    </div>
                  </div>
                </Card>

                <Card title="Role Mappings">
                   <div className="p-4 bg-emerald-950/30 border border-emerald-900/50 rounded-lg flex items-start gap-4">
                      <CheckCircle className="text-emerald-500 mt-1 flex-shrink-0" size={20} />
                      <div>
                        <h4 className="text-emerald-100 font-medium">Administrator Access</h4>
                        <p className="text-emerald-200/70 text-sm mt-1">Your account is currently mapped to the 'Owner' role via GitHub App configuration.</p>
                      </div>
                   </div>
                </Card>
              </>
            )}

            {activeTab === 'keys' && (
              <Card title="API Keys & CLI Access">
                <div className="space-y-6">
                  <p className="text-slate-400 text-sm">
                    Use API keys to authenticate with the IntelliReview CLI and REST API.
                  </p>
                  
                  <div className="p-5 bg-slate-900 rounded-lg border border-slate-800 space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-white font-medium flex items-center gap-2">
                        <Key size={16} className="text-amber-500" />
                        Default CLI Token
                      </h4>
                      <span className="text-xs bg-slate-800 px-2 py-1 rounded text-slate-300">Created Oct 24, 2026</span>
                    </div>
                    <div className="flex gap-3">
                      <input 
                        type="text" 
                        readOnly 
                        value={apiKey}
                        className="bg-slate-950 border border-slate-800 rounded-md px-3 py-2 w-full text-slate-400 font-mono text-sm"
                      />
                      <button className="bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-md transition-colors text-sm whitespace-nowrap">
                        Copy
                      </button>
                    </div>
                  </div>

                  <div className="pt-2">
                    <button className="flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors text-sm font-medium">
                      + Generate New Key
                    </button>
                  </div>
                </div>
              </Card>
            )}

            {activeTab === 'impact' && (
              <Card title="Review Impact Dashboard">
                <p className="text-slate-400 text-sm mb-6">
                  Track how your AI-assisted reviews are accelerating your team's development.
                </p>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                  <MetricBox title="Lines Reviewed" value="1.2k" trend="+12%" />
                  <MetricBox title="Issues Caught" value="29" trend="+5%" />
                  <MetricBox title="Time Saved" value="14h" trend="+20%" />
                </div>

                <div className="h-72 w-full bg-slate-900/50 p-4 rounded-xl border border-slate-800">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={mockImpactData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorIssues" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                      <XAxis dataKey="name" stroke="#475569" fontSize={12} tickLine={false} axisLine={false} />
                      <YAxis stroke="#475569" fontSize={12} tickLine={false} axisLine={false} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f1f5f9' }}
                        itemStyle={{ color: '#93c5fd' }}
                      />
                      <Area type="monotone" dataKey="issues" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorIssues)" />
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
        ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.1)]' 
        : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200 border border-transparent'
    }`}
  >
    {icon}
    <span className="font-medium">{label}</span>
  </button>
);

const Card = ({ title, children }: { title: string, children: React.ReactNode }) => (
  <div className="bg-slate-950 rounded-2xl border border-slate-800 p-6 md:p-8 shadow-xl backdrop-blur-sm relative overflow-hidden">
    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-600 to-indigo-600 opacity-50"></div>
    <h2 className="text-xl font-bold text-white mb-6 tracking-tight">{title}</h2>
    {children}
  </div>
);

const InputField = ({ label, type = "text", defaultValue = "" }: { label: string, type?: string, defaultValue?: string }) => (
  <div>
    <label className="block text-sm font-medium text-slate-400 mb-1.5">{label}</label>
    <input 
      type={type} 
      defaultValue={defaultValue}
      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all placeholder:text-slate-600"
    />
  </div>
);

const MetricBox = ({ title, value, trend }: { title: string, value: string, trend: string }) => (
  <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 border-t-2 border-t-blue-500/50">
    <h3 className="text-slate-400 text-sm font-medium">{title}</h3>
    <div className="mt-2 flex items-baseline gap-2">
      <span className="text-3xl font-bold text-white">{value}</span>
      <span className="text-xs font-medium text-emerald-400">{trend}</span>
    </div>
  </div>
);
