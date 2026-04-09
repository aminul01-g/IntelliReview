import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
  Code, AlertTriangle, CheckCircle, TrendingUp,
  LogOut, User, Home, Activity
} from 'lucide-react';

// Types
interface User {
  username: string;
}

interface Issue {
  id?: string;
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  line: number;
  message: string;
  suggestion?: string;
  quick_fix?: string;
}

interface FeedbackStats {
  statistics: Record<string, {
    total_suggestions: number;
    acceptance_rate: number;
    rejection_rate: number;
  }>;
  total_issue_types: number;
}

interface Metrics {
  total_analyses: number;
  weekly_analyses: number;
  language_breakdown: Record<string, number>;
  technical_debt_hours: number;
  user_since: string;
}

interface TrendData {
  date: string;
  count: number;
}

interface TeamMetrics {
  team_name: string;
  total_members: number;
  total_analyses: number;
  issue_distribution: Record<string, number>;
  error?: string;
}

interface AnalysisResult {
  analysis_id: number;
  status: string;
  language: string;
  file_path: string;
  metrics: {
    lines_of_code: number;
    complexity: number;
    maintainability_index?: number;
    duplication_percentage?: number;
  };
  issues: Issue[];
  processing_time?: number;
  analyzed_at: string;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
}

// Mock API service (replace with actual API calls)
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const api = {
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username, password }),
      credentials: 'include'
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }
    return response.json();
  },

  register: async (username: string, email: string, password: string): Promise<any> => {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }
    return response.json();
  },

  checkAuth: async (): Promise<User> => {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      credentials: 'include'
    });
    if (!response.ok) {
      throw new Error('Not authenticated');
    }
    return response.json();
  },

  analyze: async (code: string, language: string): Promise<AnalysisResult> => {
    const response = await fetch(`${API_BASE_URL}/analysis/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ code, language }),
      credentials: 'include'
    });
    if (!response.ok) {
      throw new Error('Analysis failed');
    }
    return response.json();
  },

  getMetrics: async (): Promise<Metrics> => {
    const response = await fetch(`${API_BASE_URL}/metrics/user`, {
      credentials: 'include'
    });
    if (!response.ok) {
      throw new Error('Failed to load metrics');
    }
    return response.json();
  },

  getTrends: async (): Promise<TrendData[]> => {
    const response = await fetch(`${API_BASE_URL}/metrics/trends`, {
      credentials: 'include'
    });
    return response.json();
  },

  getTeamMetrics: async (): Promise<TeamMetrics> => {
    const response = await fetch(`${API_BASE_URL}/metrics/team`, {
      credentials: 'include'
    });
    return response.json();
  },

  getHistory: async (): Promise<AnalysisResult[]> => {
    const response = await fetch(`${API_BASE_URL}/analysis/history`, {
      credentials: 'include'
    });
    return response.json();
  },

  submitFeedback: async (suggestion_id: string, accepted: boolean, issue_type: string): Promise<any> => {
    const response = await fetch(`${API_BASE_URL}/feedback/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ suggestion_id, accepted, issue_type }),
      credentials: 'include'
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Feedback submission failed');
    }
    return response.json();
  },

  getFeedbackStats: async (): Promise<FeedbackStats> => {
    const response = await fetch(`${API_BASE_URL}/feedback/stats`, {
      credentials: 'include'
    });
    if (!response.ok) {
      throw new Error('Failed to load feedback stats');
    }
    return response.json();
  }
};

// Main Dashboard Component
const IntelliReviewDashboard = () => {
  const [currentView, setCurrentView] = useState<string>('login');
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<User | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [trends, setTrends] = useState<TrendData[]>([]);
  const [teamMetrics, setTeamMetrics] = useState<TeamMetrics | null>(null);
  const [feedbackStats, setFeedbackStats] = useState<FeedbackStats | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [history, setHistory] = useState<AnalysisResult[]>([]);

  useEffect(() => {
    const checkSession = async () => {
      try {
        const userData = await api.checkAuth();
        setUser(userData);
        setIsAuthenticated(true);
        setCurrentView('dashboard');
      } catch (e) {
        setIsAuthenticated(false);
      }
    };
    checkSession();
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      loadAllData();
    }
  }, [isAuthenticated]);

  const loadAllData = async () => {
    try {
      const [m, t, tm, fs, h] = await Promise.all([
        api.getMetrics(),
        api.getTrends(),
        api.getTeamMetrics(),
        api.getFeedbackStats(),
        api.getHistory()
      ]);
      setMetrics(m);
      setTrends(t || []);
      setTeamMetrics(tm);
      setFeedbackStats(fs);
      setHistory(h || []);
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const handleLogin = async (username: string, password: string) => {
    try {
      await api.login(username, password);
      setIsAuthenticated(true);
      setUser({ username });
      setCurrentView('dashboard');
    } catch (error) {
      alert('Login failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  const handleRegister = async (username: string, email: string, password: string) => {
    try {
      await api.register(username, email, password);
      alert('Registration successful! Please login.');
    } catch (error) {
      alert('Registration failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setUser(null);
    setCurrentView('login');
  };

  const handleAnalyze = async (code: string, language: string) => {
    try {
      const result = await api.analyze(code, language);
      setAnalysisResult(result);
      await loadAllData();
    } catch (error) {
      alert('Analysis failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  if (currentView === 'login') {
    return <LoginScreen onLogin={handleLogin} onRegister={handleRegister} />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar
        currentView={currentView}
        setCurrentView={setCurrentView}
        user={user}
        onLogout={handleLogout}
      />

      <div className="ml-64 p-8">
        <Header user={user} />

        {currentView === 'dashboard' && (
          <DashboardView metrics={metrics} trends={trends} />
        )}

        {currentView === 'analyze' && (
          <AnalyzeView
            onAnalyze={handleAnalyze}
            result={analysisResult}
          />
        )}

        {currentView === 'metrics' && (
          <MetricsView metrics={metrics} teamMetrics={teamMetrics} feedbackStats={feedbackStats} />
        )}

        {currentView === 'history' && (
          <HistoryView history={history} onSelect={(res) => { setAnalysisResult(res); setCurrentView('analyze'); }} />
        )}
      </div>
    </div>
  );
};

interface LoginScreenProps {
  onLogin: (u: string, p: string) => void;
  onRegister: (u: string, e: string, p: string) => void;
}

const LoginScreen: React.FC<LoginScreenProps> = ({ onLogin, onRegister }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isRegister) {
      onRegister(username, email, password);
    } else {
      onLogin(username, password);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <Code className="w-16 h-16 text-blue-600 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-gray-800">IntelliReview</h1>
          <p className="text-gray-600 mt-2">AI-Powered Code Review Assistant</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUsername(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
              required
            />
          </div>

          {isRegister && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                required
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold"
          >
            {isRegister ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        <div className="text-center mt-6">
          <button 
            onClick={() => setIsRegister(!isRegister)}
            className="text-blue-600 hover:underline text-sm"
          >
            {isRegister ? 'Already have an account? Sign In' : "Don't have an account? Register"}
          </button>
        </div>
      </div>
    </div>
  );
};

interface SidebarProps {
  currentView: string;
  setCurrentView: (view: string) => void;
  user: User | null;
  onLogout: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ currentView, setCurrentView, user, onLogout }) => {
  const menuItems = [
    { id: 'dashboard', icon: Home, label: 'Dashboard' },
    { id: 'analyze', icon: Code, label: 'Analyze Code' },
    { id: 'history', icon: Activity, label: 'History' },
    { id: 'metrics', icon: Activity, label: 'Metrics' }
  ];

  return (
    <div className="fixed left-0 top-0 h-full w-64 bg-gray-900 text-white p-6">
      <div className="flex items-center space-x-3 mb-8">
        <Code className="w-8 h-8 text-blue-400" />
        <h2 className="text-xl font-bold">IntelliReview</h2>
      </div>

      <nav className="space-y-2">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setCurrentView(item.id)}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${currentView === item.id
              ? 'bg-blue-600 text-white'
              : 'text-gray-300 hover:bg-gray-800'
              }`}
          >
            <item.icon className="w-5 h-5" />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="absolute bottom-6 left-6 right-6">
        <div className="bg-gray-800 rounded-lg p-4 mb-4">
          <div className="flex items-center space-x-3">
            <User className="w-8 h-8 text-gray-400" />
            <div>
              <p className="font-medium text-sm">{user?.username || 'User'}</p>
              <p className="text-xs text-gray-400">Project Plan</p>
            </div>
          </div>
        </div>

        <button
          onClick={onLogout}
          className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>Logout</span>
        </button>
      </div>
    </div>
  );
};

interface HeaderProps {
  user: User | null;
}

const Header: React.FC<HeaderProps> = ({ user }) => {
  return (
    <div className="mb-8">
      <h1 className="text-3xl font-bold text-gray-800 font-display">
        Welcome back, {user?.username || 'Developer'}!
      </h1>
      <p className="text-gray-600 mt-2">Here's your code quality overview</p>
    </div>
  );
};

interface DashboardViewProps {
  metrics: Metrics | null;
  trends: TrendData[];
}

const DashboardView: React.FC<DashboardViewProps> = ({ metrics, trends }) => {
  const stats = [
    { label: 'Total Analyses', value: metrics?.total_analyses || 0, icon: Code, color: 'bg-blue-500' },
    { label: 'This Week', value: metrics?.weekly_analyses || 0, icon: TrendingUp, color: 'bg-green-500' },
    { label: 'Technical Debt', value: `${metrics?.technical_debt_hours || 0} hrs`, icon: AlertTriangle, color: 'bg-red-500' },
    { label: 'Health Score', value: '84%', icon: CheckCircle, color: 'bg-purple-500' }
  ];

  const languageData = metrics?.language_breakdown
    ? Object.entries(metrics.language_breakdown).map(([name, value]) => ({ name, value }))
    : [{ name: 'Python', value: 25 }, { name: 'JavaScript', value: 15 }, { name: 'Java', value: 8 }];

  const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6'];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <div key={index} className="bg-white rounded-lg shadow p-6 border-l-4 border-opacity-50">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm font-medium">{stat.label}</p>
                <p className="text-3xl font-bold text-gray-800 mt-1">{stat.value}</p>
              </div>
              <div className={`${stat.color} p-3 rounded-xl shadow-inner`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-6 flex items-center font-display">
            <TrendingUp className="w-5 h-5 mr-2 text-blue-500" />
            Analysis Velocity
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
              <XAxis dataKey="date" axisLine={false} tickLine={false} />
              <YAxis axisLine={false} tickLine={false} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="count" stroke="#3B82F6" strokeWidth={3} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-6 flex items-center font-display">
            <Activity className="w-5 h-5 mr-2 text-purple-500" />
            Language Distribution
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={languageData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                {languageData.map((_, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

interface AnalyzeViewProps {
  onAnalyze: (code: string, language: string) => Promise<void>;
  result: AnalysisResult | null;
}

const AnalyzeView: React.FC<AnalyzeViewProps> = ({ onAnalyze, result }) => {
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('python');
  const [analyzing, setAnalyzing] = useState(false);

  const handleAnalyze = async () => {
    if (!code.trim()) { alert('Please enter some code to analyze'); return; }
    setAnalyzing(true);
    try { await onAnalyze(code, language); } finally { setAnalyzing(false); }
  };

  const handleFeedback = async (suggestion_id: string, accepted: boolean, issue_type: string) => {
    try {
      await api.submitFeedback(suggestion_id, accepted, issue_type);
      alert('Thank you for your feedback!');
    } catch (error) {
      console.error('Feedback failed:', error);
    }
  };

  const severityColors: Record<string, string> = {
    critical: 'bg-red-100 text-red-800 border-red-200',
    high: 'bg-orange-100 text-orange-800 border-orange-200',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    low: 'bg-blue-100 text-blue-800 border-blue-200',
    info: 'bg-gray-100 text-gray-800 border-gray-200'
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-4 font-display">Analyze Your Code</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Language</label>
            <select value={language} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setLanguage(e.target.value)} className="w-full px-4 py-2 border rounded-lg">
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="java">Java</option>
              <option value="cpp">C++</option>
              <option value="c">C</option>
            </select>
          </div>
          <textarea value={code} onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCode(e.target.value)} rows={12} className="w-full px-4 py-3 border rounded-lg font-mono text-sm" placeholder="Paste code here..." />
          <button onClick={handleAnalyze} disabled={analyzing} className={`w-full py-3 rounded-lg font-semibold text-white ${analyzing ? 'bg-gray-400' : 'bg-blue-600 hover:bg-blue-700'}`}>
            {analyzing ? 'Analyzing...' : 'Analyze Code'}
          </button>
        </div>
      </div>

      {result && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold text-gray-800 mb-4 font-display">Analysis Results</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-blue-50 p-4 rounded-lg"><p className="text-sm text-gray-600">Lines</p><p className="text-2xl font-bold">{result.metrics?.lines_of_code || 0}</p></div>
            <div className="bg-green-50 p-4 rounded-lg"><p className="text-sm text-gray-600">Complexity</p><p className="text-2xl font-bold">{result.metrics?.complexity?.toFixed(1) || 0}</p></div>
            <div className="bg-purple-50 p-4 rounded-lg"><p className="text-sm text-gray-600">Issues</p><p className="text-2xl font-bold">{result.issues?.length || 0}</p></div>
          </div>
          {result.processing_time && <p className="text-xs text-gray-400 mb-4 italic">Analysis took {result.processing_time}s</p>}
          <div className="space-y-4">
            {result.issues && result.issues.length > 0 ? (
              result.issues.map((issue, idx) => (
                <div key={idx} className={`border rounded-lg p-4 ${severityColors[issue.severity] || 'bg-gray-100'}`}>
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-sm font-bold mb-1">Line {issue.line} - {issue.type}</p>
                      <p className="text-sm mb-2">{issue.message}</p>
                      {issue.suggestion && (
                        <div className="mt-4 p-5 bg-slate-50 rounded-xl border border-slate-200 shadow-sm transition-all hover:shadow-md">
                          <div className="flex items-center space-x-2 mb-4 pb-2 border-b border-slate-200">
                             <div className="bg-blue-100 p-1.5 rounded-lg">
                               <CheckCircle className="w-4 h-4 text-blue-600" />
                             </div>
                             <p className="text-sm font-bold text-slate-800 uppercase tracking-wide">IntelliReview Suggestion</p>
                          </div>
                          <div className="markdown-content prose prose-sm max-w-none prose-slate prose-headings:text-slate-900 prose-code:text-blue-600 prose-code:bg-blue-50 prose-code:px-1 prose-code:rounded prose-pre:bg-slate-900 prose-pre:text-slate-100">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {issue.suggestion}
                            </ReactMarkdown>
                          </div>
                          <div className="mt-6 pt-4 border-t border-slate-200 flex items-center justify-between">
                            <span className="text-xs text-slate-500 font-medium italic">Was this AI suggestion helpful?</span>
                            <div className="flex space-x-2">
                              <button onClick={() => handleFeedback(issue.id || 'unknown', true, issue.type)} className="text-xs px-4 py-2 bg-white text-emerald-700 font-bold rounded-lg border border-emerald-200 hover:bg-emerald-50 hover:border-emerald-300 transition-all flex items-center shadow-sm">
                                <CheckCircle className="w-3.5 h-3.5 mr-1.5" /> Yes
                              </button>
                              <button onClick={() => handleFeedback(issue.id || 'unknown', false, issue.type)} className="text-xs px-4 py-2 bg-white text-rose-700 font-bold rounded-lg border border-rose-200 hover:bg-rose-50 hover:border-rose-300 transition-all flex items-center shadow-sm">
                                <AlertTriangle className="w-3.5 h-3.5 mr-1.5" /> No
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                      {issue.quick_fix && <div className="mt-2 text-xs font-mono bg-blue-50 p-1 text-blue-700 rounded">Fix: {issue.quick_fix}</div>}
                    </div>
                  </div>
                </div>
              ))
            ) : <p className="text-center py-6 text-gray-500">No issues detected! 🎉</p>}
          </div>
        </div>
      )}
    </div>
  );
};

interface MetricsViewProps {
  metrics: Metrics | null;
  teamMetrics: TeamMetrics | null;
  feedbackStats: FeedbackStats | null;
}

const MetricsView: React.FC<MetricsViewProps> = ({ metrics, teamMetrics, feedbackStats }) => {
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-6 font-display">Quality & Performance</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 bg-blue-50 rounded-2xl">
            <h3 className="text-lg font-bold text-blue-800">Technical Debt</h3>
            <p className="text-4xl font-black text-blue-900 mt-2">{metrics?.technical_debt_hours || 0} hrs</p>
          </div>
          <div className="p-6 bg-indigo-50 rounded-2xl">
            <h3 className="text-lg font-bold text-indigo-800">Team Velocity</h3>
            <p className="text-4xl font-black text-indigo-900 mt-2">{teamMetrics?.total_analyses || 0} PRs</p>
          </div>
        </div>
        {teamMetrics?.issue_distribution && (
          <div className="mt-6 p-4 bg-gray-50 rounded-lg border">
            <p className="text-xs font-bold text-gray-500 uppercase mb-2">Issue Distribution</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(teamMetrics.issue_distribution).map(([name, count]) => (
                <span key={name} className="px-2 py-1 bg-white border rounded text-xs">
                  {name}: {count}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {feedbackStats && (
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-xl font-bold text-gray-800 mb-6 flex items-center font-display">
            <TrendingUp className="w-6 h-6 mr-2 text-green-500" />
            AI Suggestion Acceptance
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(feedbackStats.statistics).map(([type, data]) => (
              <div key={type} className="p-4 bg-gray-50 rounded-lg border">
                <p className="text-xs font-bold text-gray-500 uppercase">{type}</p>
                <p className="text-2xl font-bold text-gray-800">{Math.round(data.acceptance_rate * 100)}%</p>
                <div className="w-full bg-gray-200 h-1 rounded-full mt-2"><div className="bg-green-500 h-1 rounded-full" style={{ width: `${data.acceptance_rate * 100}%` }} /></div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const HistoryView: React.FC<{ history: AnalysisResult[], onSelect: (res: AnalysisResult) => void }> = ({ history, onSelect }) => {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-6 font-display">Analysis History</h2>
      {history.length === 0 ? (
        <p className="text-gray-500 text-center py-12">No analyses performed yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                <th className="pb-4">File</th>
                <th className="pb-4">Language</th>
                <th className="pb-4">Issues</th>
                <th className="pb-4">Date</th>
                <th className="pb-4">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {history.map((item) => (
                <tr key={item.analysis_id} className="hover:bg-gray-50 transition-colors">
                  <td className="py-4 font-medium text-gray-700">{item.file_path}</td>
                  <td className="py-4"><span className="px-2 py-1 bg-blue-50 text-blue-600 rounded text-xs">{item.language}</span></td>
                  <td className="py-4 text-center"><span className="font-bold">{item.issues.length}</span></td>
                  <td className="py-4 text-sm text-gray-500">{new Date(item.analyzed_at).toLocaleDateString()}</td>
                  <td className="py-4"><button onClick={() => onSelect(item)} className="text-blue-600 hover:text-blue-800 font-semibold text-sm">View Report</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default IntelliReviewDashboard;