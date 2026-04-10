import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
  Code, AlertTriangle, CheckCircle, TrendingUp,
  LogOut, User, Home, Activity, Upload
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
  confidence?: number;
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

interface ProjectRecord {
  id: number;
  name: string;
  plan_md: string | null;
  created_at: string;
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

interface FileResult {
  analysis_id: number;
  file_path: string;
  language: string;
  metrics: {
    lines_of_code: number;
    complexity: number | null;
    maintainability_index: number | null;
    duplication_percentage: number | null;
  };
  issue_count: number;
  severity_counts: Record<string, number>;
  issues: Issue[];
  status: string;
  related_files?: string[];
}

interface AutoFix {
  filename: string;
  diff: string;
  issues_addressed: number;
  status: string;
}

interface ProjectUploadResult {
  project_summary: {
    total_files: number;
    total_lines: number;
    total_issues: number;
    health_score: number;
    language_breakdown: Record<string, number>;
    processing_time: number;
  };
  ai_project_review?: string;
  auto_fixes?: AutoFix[];
  file_results: FileResult[];
  skipped: { file: string; reason: string }[];
  errors: { file: string; error: string }[];
}

// Mock API service (replace with actual API calls)
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const handleApiError = async (response: Response) => {
  let errorMessage = `HTTP Error ${response.status} - API Request failed.`;
  try {
    const errorData = await response.json();
    errorMessage = errorData.detail || errorData.error || errorMessage;
  } catch (e) {
    try {
      const text = await response.text();
      if (text) errorMessage = `Server Error: ${text.substring(0, 100)}`;
    } catch (inner) {}
  }
  throw new Error(errorMessage);
};

const api = {
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username, password }),
      credentials: 'include'
    });
    if (!response.ok) await handleApiError(response);
    return await response.json();
  },

  register: async (username: string, email: string, password: string): Promise<any> => {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password }),
    });
    if (!response.ok) await handleApiError(response);
    return await response.json();
  },

  checkAuth: async (): Promise<User> => {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      credentials: 'include'
    });
    if (!response.ok) {
       throw new Error('Not authenticated');
    }
    return await response.json();
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
    if (!response.ok) await handleApiError(response);
    return await response.json();
  },

  getMetrics: async (): Promise<Metrics> => {
    const response = await fetch(`${API_BASE_URL}/metrics/user`, {
      credentials: 'include'
    });
    if (!response.ok) await handleApiError(response);
    return await response.json();
  },

  getTrends: async (): Promise<TrendData[]> => {
    const response = await fetch(`${API_BASE_URL}/metrics/trends`, {
      credentials: 'include'
    });
    if (!response.ok) await handleApiError(response);
    return await response.json();
  },

  getTeamMetrics: async (): Promise<TeamMetrics> => {
    const response = await fetch(`${API_BASE_URL}/metrics/team`, {
      credentials: 'include'
    });
    if (!response.ok) await handleApiError(response);
    return await response.json();
  },

  getHistory: async (): Promise<AnalysisResult[]> => {
    const response = await fetch(`${API_BASE_URL}/analysis/history`, {
      credentials: 'include'
    });
    if (!response.ok) await handleApiError(response);
    return await response.json();
  },

  getProjects: async (): Promise<ProjectRecord[]> => {
    const response = await fetch(`${API_BASE_URL}/analysis/projects`, {
      credentials: 'include'
    });
    if (!response.ok) await handleApiError(response);
    return await response.json();
  },

  submitFeedback: async (suggestion_id: string, accepted: boolean, issue_type: string): Promise<any> => {
    const response = await fetch(`${API_BASE_URL}/feedback/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ suggestion_id, accepted, issue_type }),
      credentials: 'include'
    });
    if (!response.ok) await handleApiError(response);
    return await response.json();
  },

  getFeedbackStats: async (): Promise<FeedbackStats> => {
    const response = await fetch(`${API_BASE_URL}/feedback/stats`, {
      credentials: 'include'
    });
    if (!response.ok) await handleApiError(response);
    return await response.json();
  },

  uploadFiles: async (files: FileList): Promise<ProjectUploadResult> => {
    const formData = new FormData();
    const commonIgnores = ['node_modules', '.git', '.venv', 'venv', '__pycache__', 'build', 'dist', '.next', 'coverage'];
    const binaryExts = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.mp3', '.zip', '.tar', '.gz', '.pdf', '.exe', '.dll', '.so'];
    
    let addedCount = 0;
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const path = file.webkitRelativePath || file.name;
        
        // Skip ignored directories
        if (commonIgnores.some(ignore => path.includes(`/${ignore}/`) || path.startsWith(`${ignore}/`))) continue;
        
        // Skip binary extensions
        if (binaryExts.some(ext => path.toLowerCase().endsWith(ext))) continue;
        
        // Prevent browser crashes by capping at a very large safe limit (5000 files)
        if (addedCount >= 5000) break;
        
        // Pass the full relative nested path so IntelliReview preserves the directory structure!
        formData.append('files', file, path);
        addedCount++;
    }
    
    // If no valid files remain after filtering
    if (addedCount === 0) {
        throw new Error("No valid code files found in selection. Ensure you are not uploading ignored folders (node_modules, etc).");
    }

    const response = await fetch(`${API_BASE_URL}/analysis/upload`, {
      method: 'POST',
      body: formData,
      credentials: 'include'
    });
    if (!response.ok) await handleApiError(response);
    return await response.json();
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
  const [projects, setProjects] = useState<ProjectRecord[]>([]);

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
      const [m, t, tm, fs, h, pList] = await Promise.all([
        api.getMetrics(),
        api.getTrends(),
        api.getTeamMetrics(),
        api.getFeedbackStats(),
        api.getHistory(),
        api.getProjects()
      ]);
      setMetrics(m);
      setTrends(t || []);
      setTeamMetrics(tm);
      setFeedbackStats(fs);
      setHistory(h || []);
      setProjects(pList || []);
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

        {currentView === 'upload' && (
          <ProjectUploadView />
        )}

        {currentView === 'metrics' && (
          <MetricsView metrics={metrics} teamMetrics={teamMetrics} feedbackStats={feedbackStats} />
        )}

        {currentView === 'history' && (
          <HistoryView history={history} projects={projects} onSelect={(res) => { setAnalysisResult(res); setCurrentView('analyze'); }} />
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
    { id: 'upload', icon: Upload, label: 'Upload Project' },
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
  const [expandedSeverity, setExpandedSeverity] = useState<Record<string, boolean>>({
    critical: true, high: true, medium: false, low: false, info: false
  });

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

  // Separate AI overview from regular issues
  const aiOverview = result?.issues?.find(i => i.type === 'ai_overview');
  const regularIssues = result?.issues?.filter(i => i.type !== 'ai_overview') || [];

  // Group issues by severity
  const severityOrder = ['critical', 'high', 'medium', 'low', 'info'];
  const groupedIssues: Record<string, Issue[]> = {};
  for (const issue of regularIssues) {
    const sev = issue.severity || 'info';
    if (!groupedIssues[sev]) groupedIssues[sev] = [];
    groupedIssues[sev].push(issue);
  }

  const severityConfig: Record<string, { label: string; border: string; bg: string; badge: string; text: string; dot: string }> = {
    critical: { label: 'Critical', border: 'border-red-300', bg: 'bg-red-50', badge: 'bg-red-600 text-white', text: 'text-red-800', dot: 'bg-red-500' },
    high:     { label: 'High',     border: 'border-orange-300', bg: 'bg-orange-50', badge: 'bg-orange-500 text-white', text: 'text-orange-800', dot: 'bg-orange-500' },
    medium:   { label: 'Medium',   border: 'border-yellow-300', bg: 'bg-yellow-50', badge: 'bg-yellow-500 text-white', text: 'text-yellow-800', dot: 'bg-yellow-500' },
    low:      { label: 'Low',      border: 'border-blue-300', bg: 'bg-blue-50', badge: 'bg-blue-500 text-white', text: 'text-blue-800', dot: 'bg-blue-500' },
    info:     { label: 'Info',     border: 'border-gray-300', bg: 'bg-gray-50', badge: 'bg-gray-500 text-white', text: 'text-gray-700', dot: 'bg-gray-400' },
  };

  const toggleSeverity = (sev: string) => {
    setExpandedSeverity(prev => ({ ...prev, [sev]: !prev[sev] }));
  };

  return (
    <div className="space-y-6">
      {/* Code Input Section */}
      <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
        <h2 className="text-2xl font-bold text-gray-800 mb-4 font-display flex items-center">
          <Code className="w-6 h-6 mr-2 text-blue-500" />
          Analyze Your Code
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Language</label>
            <select value={language} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setLanguage(e.target.value)} className="w-full px-4 py-2 border border-gray-200 rounded-lg bg-gray-50 focus:ring-2 focus:ring-blue-400 focus:border-transparent transition-all">
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="java">Java</option>
              <option value="cpp">C++</option>
              <option value="c">C</option>
            </select>
          </div>
          <textarea value={code} onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCode(e.target.value)} rows={12} className="w-full px-4 py-3 border border-gray-200 rounded-lg font-mono text-sm bg-gray-900 text-gray-100 focus:ring-2 focus:ring-blue-400 focus:border-transparent transition-all" placeholder="Paste your code here..." />
          <button onClick={handleAnalyze} disabled={analyzing} className={`w-full py-3 rounded-lg font-semibold text-white transition-all ${analyzing ? 'bg-gray-400 cursor-not-allowed' : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-lg hover:shadow-xl'}`}>
            {analyzing ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                Analyzing...
              </span>
            ) : 'Analyze Code'}
          </button>
        </div>
      </div>

      {/* Results Section */}
      {result && (
        <div className="space-y-6">
          {/* Metrics Summary Bar */}
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-gray-800 font-display">Analysis Results</h3>
              {result.processing_time && <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">⏱ {result.processing_time}s</span>}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-xl border border-blue-200">
                <p className="text-xs font-semibold text-blue-600 uppercase tracking-wider">Lines</p>
                <p className="text-2xl font-black text-blue-900 mt-1">{result.metrics?.lines_of_code || 0}</p>
              </div>
              <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-xl border border-green-200">
                <p className="text-xs font-semibold text-green-600 uppercase tracking-wider">Complexity</p>
                <p className="text-2xl font-black text-green-900 mt-1">{result.metrics?.complexity?.toFixed(1) || '0'}</p>
              </div>
              <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-xl border border-purple-200">
                <p className="text-xs font-semibold text-purple-600 uppercase tracking-wider">Issues</p>
                <p className="text-2xl font-black text-purple-900 mt-1">{regularIssues.length}</p>
              </div>
              <div className="bg-gradient-to-br from-amber-50 to-amber-100 p-4 rounded-xl border border-amber-200">
                <p className="text-xs font-semibold text-amber-600 uppercase tracking-wider">Maintainability</p>
                <p className="text-2xl font-black text-amber-900 mt-1">{result.metrics?.maintainability_index?.toFixed(0) || 'N/A'}</p>
              </div>
            </div>
          </div>

          {/* Executive AI Overview Panel */}
          {aiOverview?.suggestion && (
            <div className="bg-white rounded-xl shadow-lg border-2 border-indigo-200 overflow-hidden">
              <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-600 px-6 py-4">
                <div className="flex items-center space-x-3">
                  <div className="bg-white/20 p-2 rounded-lg backdrop-blur-sm">
                    <CheckCircle className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white">Executive AI Code Review</h3>
                    <p className="text-indigo-200 text-xs">Powered by IntelliReview AI Engine</p>
                  </div>
                </div>
              </div>
              <div className="p-6">
                <div className="prose prose-sm max-w-none prose-slate prose-headings:text-slate-900 prose-headings:font-bold prose-h2:text-base prose-h2:mt-4 prose-h2:mb-2 prose-code:text-indigo-600 prose-code:bg-indigo-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-pre:bg-slate-900 prose-pre:text-slate-100 prose-pre:rounded-xl prose-table:text-sm prose-th:bg-slate-100 prose-th:px-3 prose-th:py-2 prose-td:px-3 prose-td:py-2 prose-li:my-0.5">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {aiOverview.suggestion}
                  </ReactMarkdown>
                </div>
                <div className="mt-6 pt-4 border-t border-slate-200 flex items-center justify-between">
                  <span className="text-xs text-slate-500 font-medium italic">Was this AI review helpful?</span>
                  <div className="flex space-x-2">
                    <button onClick={() => handleFeedback('overview', true, 'ai_overview')} className="text-xs px-4 py-2 bg-white text-emerald-700 font-bold rounded-lg border border-emerald-200 hover:bg-emerald-50 hover:border-emerald-300 transition-all flex items-center shadow-sm">
                      <CheckCircle className="w-3.5 h-3.5 mr-1.5" /> Yes
                    </button>
                    <button onClick={() => handleFeedback('overview', false, 'ai_overview')} className="text-xs px-4 py-2 bg-white text-rose-700 font-bold rounded-lg border border-rose-200 hover:bg-rose-50 hover:border-rose-300 transition-all flex items-center shadow-sm">
                      <AlertTriangle className="w-3.5 h-3.5 mr-1.5" /> No
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Grouped Issue Cards */}
          {regularIssues.length > 0 ? (
            <div className="space-y-4">
              <h3 className="text-lg font-bold text-gray-800 font-display flex items-center">
                <AlertTriangle className="w-5 h-5 mr-2 text-amber-500" />
                Detected Issues ({regularIssues.length})
              </h3>

              {severityOrder.map(sev => {
                const issues = groupedIssues[sev];
                if (!issues || issues.length === 0) return null;
                const config = severityConfig[sev];
                const isExpanded = expandedSeverity[sev];

                return (
                  <div key={sev} className={`bg-white rounded-xl shadow border ${config.border} overflow-hidden`}>
                    {/* Severity Group Header */}
                    <button
                      onClick={() => toggleSeverity(sev)}
                      className={`w-full flex items-center justify-between px-5 py-3 ${config.bg} hover:brightness-95 transition-all`}
                    >
                      <div className="flex items-center space-x-3">
                        <span className={`w-2.5 h-2.5 rounded-full ${config.dot}`}></span>
                        <span className={`font-bold text-sm ${config.text}`}>{config.label}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${config.badge}`}>{issues.length}</span>
                      </div>
                      <svg className={`w-4 h-4 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                    </button>

                    {/* Expanded Issue List */}
                    {isExpanded && (
                      <div className="divide-y divide-gray-100">
                        {issues.map((issue, idx) => (
                          <div key={idx} className="px-5 py-4 hover:bg-gray-50 transition-colors">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center space-x-2 mb-1">
                                  <span className="text-xs font-mono bg-gray-200 text-gray-700 px-2 py-0.5 rounded">L{issue.line}</span>
                                  <span className="text-sm font-semibold text-gray-800">{issue.type.replace(/_/g, ' ')}</span>
                                  {issue.confidence && <span className="text-xs text-gray-400">{Math.round(issue.confidence * 100)}% confidence</span>}
                                </div>
                                <p className="text-sm text-gray-600">{issue.message}</p>

                                {/* Compact AI Suggestion */}
                                {issue.suggestion && (
                                  <div className="mt-3 p-4 bg-slate-50 rounded-lg border border-slate-200">
                                    <div className="flex items-center space-x-1.5 mb-2">
                                      <CheckCircle className="w-3.5 h-3.5 text-blue-500" />
                                      <span className="text-xs font-bold text-slate-600 uppercase tracking-wide">AI Fix</span>
                                    </div>
                                    <div className="prose prose-xs max-w-none prose-slate prose-code:text-blue-600 prose-code:bg-blue-50 prose-code:px-1 prose-code:rounded prose-pre:bg-slate-900 prose-pre:text-slate-100 prose-pre:rounded-lg prose-pre:text-xs prose-p:text-sm prose-p:my-1">
                                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {issue.suggestion}
                                      </ReactMarkdown>
                                    </div>
                                    <div className="mt-3 pt-2 border-t border-slate-200 flex items-center justify-end space-x-2">
                                      <button onClick={() => handleFeedback(issue.id || `issue-${idx}`, true, issue.type)} className="text-xs px-3 py-1.5 bg-white text-emerald-700 font-semibold rounded border border-emerald-200 hover:bg-emerald-50 transition-all flex items-center">
                                        <CheckCircle className="w-3 h-3 mr-1" /> Helpful
                                      </button>
                                      <button onClick={() => handleFeedback(issue.id || `issue-${idx}`, false, issue.type)} className="text-xs px-3 py-1.5 bg-white text-rose-700 font-semibold rounded border border-rose-200 hover:bg-rose-50 transition-all flex items-center">
                                        <AlertTriangle className="w-3 h-3 mr-1" /> Not helpful
                                      </button>
                                    </div>
                                  </div>
                                )}

                                {issue.quick_fix && <div className="mt-2 text-xs font-mono bg-blue-50 px-2 py-1 text-blue-700 rounded inline-block">Quick fix: {issue.quick_fix}</div>}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-lg p-12 text-center border border-gray-100">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
              <p className="text-lg font-bold text-gray-800">No issues detected!</p>
              <p className="text-sm text-gray-500 mt-1">Your code looks clean. 🎉</p>
            </div>
          )}
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

const HistoryView: React.FC<{ history: AnalysisResult[], projects: ProjectRecord[], onSelect: (res: AnalysisResult) => void }> = ({ history, projects, onSelect }) => {
  const [activeTab, setActiveTab] = useState<'projects' | 'snippets'>('projects');
  const [expandedProject, setExpandedProject] = useState<number | null>(null);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-6 font-display">Analysis History</h2>
      
      {/* Tabs */}
      <div className="flex space-x-4 border-b border-gray-200 mb-6">
        <button
          className={`py-2 px-4 border-b-2 font-medium text-sm focus:outline-none transition-colors ${
            activeTab === 'projects' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
          onClick={() => setActiveTab('projects')}
        >
          Project Folders
        </button>
        <button
          className={`py-2 px-4 border-b-2 font-medium text-sm focus:outline-none transition-colors ${
            activeTab === 'snippets' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
          onClick={() => setActiveTab('snippets')}
        >
          Loose Files
        </button>
      </div>

      {activeTab === 'projects' && (
        <div>
          {projects.length === 0 ? (
            <p className="text-gray-500 text-center py-12">No project folders uploaded yet.</p>
          ) : (
             <div className="space-y-4">
               {projects.map(p => (
                 <div key={p.id} className="border border-gray-200 rounded-lg overflow-hidden">
                   <div 
                     className="bg-gray-50 px-4 py-4 cursor-pointer hover:bg-gray-100 flex justify-between items-center"
                     onClick={() => setExpandedProject(expandedProject === p.id ? null : p.id)}
                   >
                     <div>
                       <h3 className="font-bold text-indigo-900 flex items-center gap-2">
                         <span className="text-xl">📁</span> {p.name}
                       </h3>
                       <p className="text-xs text-gray-500 mt-1">Uploaded: {new Date(p.created_at).toLocaleString()}</p>
                     </div>
                     <button className="text-indigo-600 text-sm font-semibold">
                       {expandedProject === p.id ? 'Hide Plan' : 'View Architecture Plan'}
                     </button>
                   </div>
                   
                   {expandedProject === p.id && (
                     <div className="p-6 bg-white border-t border-gray-200">
                       <h4 className="text-lg font-bold text-gray-800 mb-4 border-b pb-2">AI Architectural Plan</h4>
                       <div className="prose prose-sm max-w-none text-gray-700">
                         <ReactMarkdown remarkPlugins={[remarkGfm]}>
                           {p.plan_md || "*No architectural plan generated.*"}
                         </ReactMarkdown>
                       </div>
                     </div>
                   )}
                 </div>
               ))}
             </div>
          )}
        </div>
      )}

      {activeTab === 'snippets' && (
        <div>
          {history.length === 0 ? (
            <p className="text-gray-500 text-center py-12">No standalone files analyzed yet.</p>
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
      )}
    </div>
  );
};

export default IntelliReviewDashboard;

// ===================== PROJECT UPLOAD VIEW =====================

const ProjectUploadView: React.FC = () => {
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<ProjectUploadResult | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const fileInputRef = React.useRef(null) as any;
  const folderInputRef = React.useRef(null) as any;

  const handleUpload = async (files: FileList) => {
    if (files.length === 0) return;
    setUploading(true);
    setResult(null);
    try {
      const res = await api.uploadFiles(files);
      setResult(res);
    } catch (error) {
      alert('Upload failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: any) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      handleUpload(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e: any) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = () => setDragOver(false);

  const severityDot: Record<string, string> = {
    critical: 'bg-red-500', high: 'bg-orange-500', medium: 'bg-yellow-500', low: 'bg-blue-400', info: 'bg-gray-400'
  };

  const langColors: Record<string, string> = {
    python: 'bg-blue-100 text-blue-700',
    javascript: 'bg-yellow-100 text-yellow-700',
    java: 'bg-red-100 text-red-700',
    c: 'bg-gray-100 text-gray-700',
    cpp: 'bg-purple-100 text-purple-700',
  };

  const healthColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  const healthEmoji = (score: number) => {
    if (score >= 80) return '🟢';
    if (score >= 50) return '🟡';
    return '🔴';
  };

  // Find the selected file's details
  const selectedFileResult = result?.file_results.find(f => f.file_path === selectedFile);

  return (
    <div className="space-y-6">
      {/* Upload Zone */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-2 font-display flex items-center">
          <Upload className="w-6 h-6 mr-2 text-indigo-500" />
          Upload Project
        </h2>
        <p className="text-sm text-gray-500 mb-6">Upload files or entire folders for batch analysis. We natively support all universal programming languages!</p>

        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer ${
            dragOver
              ? 'border-indigo-400 bg-indigo-50 scale-[1.01]'
              : 'border-gray-300 bg-gray-50 hover:border-indigo-300 hover:bg-indigo-50/50'
          }`}
          onClick={() => fileInputRef.current?.click()}
        >
          {uploading ? (
            <div className="flex flex-col items-center">
              <svg className="animate-spin h-10 w-10 text-indigo-500 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              <p className="text-indigo-600 font-semibold">Analyzing your project...</p>
              <p className="text-xs text-gray-400 mt-1">This may take a moment for large projects</p>
            </div>
          ) : (
            <div>
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-700 font-semibold text-lg">Drag & drop files here</p>
              <p className="text-gray-400 text-sm mt-1">or click to browse</p>
            </div>
          )}
        </div>

        {/* Hidden file inputs */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && handleUpload(e.target.files)}
        />
        <input
          ref={folderInputRef}
          type="file"
          className="hidden"
          onChange={(e) => e.target.files && handleUpload(e.target.files)}
          {...({ webkitdirectory: '', directory: '' } as any)}
        />

        <div className="flex gap-3 mt-4">
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex-1 py-2.5 px-4 bg-white border border-gray-200 rounded-lg text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-all flex items-center justify-center"
          >
            <Code className="w-4 h-4 mr-2" /> Select Files
          </button>
          <button
            onClick={() => folderInputRef.current?.click()}
            disabled={uploading}
            className="flex-1 py-2.5 px-4 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg text-sm font-semibold text-white hover:from-indigo-700 hover:to-purple-700 transition-all flex items-center justify-center shadow-lg"
          >
            <Upload className="w-4 h-4 mr-2" /> Select Folder
          </button>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Project Health Dashboard */}
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
            <h3 className="text-xl font-bold text-gray-800 mb-4 font-display">Project Health Dashboard</h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="bg-gradient-to-br from-indigo-50 to-indigo-100 p-4 rounded-xl border border-indigo-200 text-center">
                <p className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">Health Score</p>
                <p className={`text-3xl font-black mt-1 ${healthColor(result.project_summary.health_score)}`}>
                  {healthEmoji(result.project_summary.health_score)} {result.project_summary.health_score}%
                </p>
              </div>
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-xl border border-blue-200 text-center">
                <p className="text-xs font-semibold text-blue-600 uppercase tracking-wider">Files</p>
                <p className="text-3xl font-black text-blue-900 mt-1">{result.project_summary.total_files}</p>
              </div>
              <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-xl border border-green-200 text-center">
                <p className="text-xs font-semibold text-green-600 uppercase tracking-wider">Lines</p>
                <p className="text-3xl font-black text-green-900 mt-1">{result.project_summary.total_lines?.toLocaleString()}</p>
              </div>
              <div className="bg-gradient-to-br from-red-50 to-red-100 p-4 rounded-xl border border-red-200 text-center">
                <p className="text-xs font-semibold text-red-600 uppercase tracking-wider">Issues</p>
                <p className="text-3xl font-black text-red-900 mt-1">{result.project_summary.total_issues}</p>
              </div>
              <div className="bg-gradient-to-br from-amber-50 to-amber-100 p-4 rounded-xl border border-amber-200 text-center">
                <p className="text-xs font-semibold text-amber-600 uppercase tracking-wider">Time</p>
                <p className="text-3xl font-black text-amber-900 mt-1">{result.project_summary.processing_time}s</p>
              </div>
            </div>

            {/* Language Breakdown */}
            {result.project_summary.language_breakdown && Object.keys(result.project_summary.language_breakdown).length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {Object.entries(result.project_summary.language_breakdown).map(([lang, count]) => (
                  <span key={lang} className={`px-3 py-1 rounded-full text-xs font-bold ${langColors[lang] || 'bg-gray-100 text-gray-700'}`}>
                    {lang}: {count} file{count > 1 ? 's' : ''}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* AI Project Audit Report */}
          {result.ai_project_review && (
            <div className="bg-white rounded-xl shadow-lg border-2 border-emerald-200 overflow-hidden">
              <div className="bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 px-6 py-4">
                <div className="flex items-center space-x-3">
                  <div className="bg-white/20 p-2 rounded-lg backdrop-blur-sm">
                    <CheckCircle className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white">AI Project Audit Report</h3>
                    <p className="text-emerald-200 text-xs">Holistic architectural analysis by IntelliReview Agent</p>
                  </div>
                </div>
              </div>
              <div className="p-6">
                <div className="prose prose-sm max-w-none prose-slate prose-headings:text-slate-900 prose-headings:font-bold prose-h2:text-base prose-h2:mt-5 prose-h2:mb-2 prose-code:text-emerald-600 prose-code:bg-emerald-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-pre:bg-slate-900 prose-pre:text-slate-100 prose-pre:rounded-xl prose-table:text-sm prose-th:bg-slate-100 prose-th:px-3 prose-th:py-2 prose-td:px-3 prose-td:py-2 prose-li:my-0.5">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {result.ai_project_review}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          )}

          {/* File Results Table */}
          <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-lg font-bold text-gray-800 font-display">File-by-File Results</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    <th className="px-6 py-3">File</th>
                    <th className="px-6 py-3">Language</th>
                    <th className="px-6 py-3">Lines</th>
                    <th className="px-6 py-3">Issues</th>
                    <th className="px-6 py-3">Severity</th>
                    <th className="px-6 py-3">Complexity</th>
                    <th className="px-6 py-3">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {result.file_results.map((file, idx) => (
                    <tr key={idx} className={`hover:bg-gray-50 transition-colors ${selectedFile === file.file_path ? 'bg-indigo-50' : ''}`}>
                      <td className="px-6 py-3">
                        <span className="text-sm font-medium text-gray-800 font-mono">{file.file_path}</span>
                      </td>
                      <td className="px-6 py-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${langColors[file.language] || 'bg-gray-100 text-gray-700'}`}>{file.language}</span>
                      </td>
                      <td className="px-6 py-3 text-sm text-gray-600">{file.metrics.lines_of_code}</td>
                      <td className="px-6 py-3">
                        <span className={`text-sm font-bold ${file.issue_count > 0 ? 'text-red-600' : 'text-green-600'}`}>{file.issue_count}</span>
                      </td>
                      <td className="px-6 py-3">
                        <div className="flex gap-1">
                          {Object.entries(file.severity_counts).map(([sev, count]) => (
                            <span key={sev} className="flex items-center gap-0.5 text-xs">
                              <span className={`w-2 h-2 rounded-full ${severityDot[sev] || 'bg-gray-400'}`}></span>
                              {count}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-6 py-3 text-sm text-gray-600">{file.metrics.complexity?.toFixed(1) || 'N/A'}</td>
                      <td className="px-6 py-3">
                        <button
                          onClick={() => setSelectedFile(selectedFile === file.file_path ? null : file.file_path)}
                          className="text-indigo-600 hover:text-indigo-800 font-semibold text-xs"
                        >
                          {selectedFile === file.file_path ? 'Hide' : 'View Issues'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Expanded File Detail */}
          {selectedFileResult && (
            <div className="bg-white rounded-xl shadow-lg border-2 border-indigo-200 p-6">
              <h4 className="text-lg font-bold text-gray-800 mb-2 font-mono">{selectedFileResult.file_path}</h4>
              
              {selectedFileResult.related_files && selectedFileResult.related_files.length > 0 && (
                <div className="mb-4 bg-indigo-50/50 p-3 rounded-lg border border-indigo-100 flex items-start gap-2">
                  <TrendingUp className="w-4 h-4 text-indigo-500 mt-0.5" />
                  <div>
                    <h5 className="text-xs font-bold text-indigo-800 mb-1 uppercase tracking-wider">RAG Dependency Map</h5>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                       {selectedFileResult.related_files.map((rel, ri) => (
                         <span key={ri} className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-mono border border-indigo-200">
                           {rel}
                         </span>
                       ))}
                    </div>
                  </div>
                </div>
              )}

              {selectedFileResult.issues.length > 0 ? (
                <div className="space-y-3">
                  {selectedFileResult.issues.map((issue, idx) => (
                    <div key={idx} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                      <span className={`w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0 ${severityDot[issue.severity] || 'bg-gray-400'}`}></span>
                      <div>
                        <div className="flex items-center space-x-2 mb-0.5">
                          <span className="text-xs font-mono bg-gray-200 text-gray-700 px-2 py-0.5 rounded">L{issue.line}</span>
                          <span className="text-sm font-semibold text-gray-800">{issue.type.replace(/_/g, ' ')}</span>
                        </div>
                        <p className="text-sm text-gray-600">{issue.message}</p>
                        {issue.suggestion && (
                          <p className="text-xs text-indigo-600 mt-1 italic">{issue.suggestion}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-gray-500 py-4">No issues found in this file. ✅</p>
              )}
            </div>
          )}

          {/* AI Auto-Fixes */}
          {result.auto_fixes && result.auto_fixes.length > 0 && (
            <div className="bg-white rounded-xl shadow-lg border-2 border-green-200 overflow-hidden">
              <div className="bg-gradient-to-r from-green-600 to-emerald-600 px-6 py-4">
                <div className="flex items-center space-x-3">
                  <div className="bg-white/20 p-2 rounded-lg backdrop-blur-sm">
                     <Code className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white">AI Auto-Fixes Generated</h3>
                    <p className="text-green-100 text-xs font-medium">Auto-remediation created ready-to-test diff patches for critical vulnerabilities.</p>
                  </div>
                </div>
              </div>
              <div className="p-6 space-y-6">
                {result.auto_fixes.map((fix, idx) => (
                  <div key={idx} className="border border-gray-200 rounded-lg overflow-hidden shadow-sm">
                    <div className="bg-gray-100 px-4 py-2 border-b border-gray-200 flex items-center justify-between">
                      <span className="font-mono text-sm font-bold text-gray-700">{fix.filename}</span>
                      <span className="text-xs font-bold bg-green-100 text-green-800 px-2 py-0.5 rounded-full border border-green-200 shadow-sm">
                        Fixed {fix.issues_addressed} issues
                      </span>
                    </div>
                    <div className="bg-slate-900 p-4 overflow-x-auto text-sm text-gray-300 font-mono">
                      {fix.diff.split('\n').map((line, i) => (
                        <div key={i} className={`whitespace-pre ${line.startsWith('+') ? 'text-green-400 bg-green-900/30 w-full px-1' : line.startsWith('-') ? 'text-red-400 bg-red-900/30 w-full px-1' : 'px-1'}`}>
                          {line || ' '}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Skipped & Errors */}
          {(result.skipped.length > 0 || result.errors.length > 0) && (
            <div className="bg-white rounded-xl shadow border border-gray-200 p-5">
              <h4 className="text-sm font-bold text-gray-600 uppercase tracking-wider mb-3">Skipped & Errors</h4>
              {result.skipped.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs font-semibold text-gray-500 mb-1">Skipped ({result.skipped.length})</p>
                  <div className="flex flex-wrap gap-1">
                    {result.skipped.slice(0, 20).map((s, i) => (
                      <span key={i} className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded" title={s.reason}>{s.file}</span>
                    ))}
                    {result.skipped.length > 20 && <span className="text-xs text-gray-400">+{result.skipped.length - 20} more</span>}
                  </div>
                </div>
              )}
              {result.errors.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-red-500 mb-1">Errors ({result.errors.length})</p>
                  {result.errors.map((e, i) => (
                    <p key={i} className="text-xs text-red-600">{e.file}: {e.error}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};