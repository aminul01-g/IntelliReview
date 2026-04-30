import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Code, ArrowRight, ShieldCheck, Zap, Activity } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

// ── Typewriter Code Analysis Demo ──────────────────────────────────────

const codeLines = [
  { text: 'import sqlite3', delay: 60 },
  { text: '', delay: 200 },
  { text: 'def get_user(name):', delay: 60 },
  { text: '    conn = sqlite3.connect("db")', delay: 50 },
  { text: '    query = f"SELECT * FROM users WHERE name=\'{name}\'"', delay: 40, issue: true },
  { text: '    return conn.execute(query)', delay: 50 },
  { text: '', delay: 200 },
  { text: 'password = "admin123"', delay: 50, issue: true },
  { text: 'eval(user_input)', delay: 50, issue: true },
]

const issueAnnotations = [
  { line: 4, severity: 'CRITICAL', msg: 'SQL Injection — CWE-89', color: '#ef4444', delay: 1800 },
  { line: 7, severity: 'CRITICAL', msg: 'Hardcoded password — CWE-798', color: '#ef4444', delay: 2800 },
  { line: 8, severity: 'HIGH', msg: 'eval() usage — CWE-95', color: '#f97316', delay: 3400 },
]

function TypewriterDemo() {
  const [displayedLines, setDisplayedLines] = useState<string[]>([])
  const [currentLine, setCurrentLine] = useState(0)
  const [currentChar, setCurrentChar] = useState(0)
  const [visibleIssues, setVisibleIssues] = useState<number[]>([])
  const [scanPhase, setScanPhase] = useState<'typing' | 'scanning' | 'done'>('typing')

  // Typewriter effect
  useEffect(() => {
    if (currentLine >= codeLines.length) {
      setScanPhase('scanning')
      return
    }

    const line = codeLines[currentLine]
    if (currentChar <= line.text.length) {
      const timer = setTimeout(() => {
        setDisplayedLines((prev) => {
          const copy = [...prev]
          copy[currentLine] = line.text.substring(0, currentChar)
          return copy
        })
        setCurrentChar((c) => c + 1)
      }, line.delay || 50)
      return () => clearTimeout(timer)
    } else {
      setCurrentLine((l) => l + 1)
      setCurrentChar(0)
    }
  }, [currentLine, currentChar])

  // Issue annotations appear during scan phase
  useEffect(() => {
    if (scanPhase !== 'scanning') return

    issueAnnotations.forEach((issue, idx) => {
      setTimeout(() => {
        setVisibleIssues((prev) => [...prev, idx])
        if (idx === issueAnnotations.length - 1) {
          setTimeout(() => setScanPhase('done'), 800)
        }
      }, (idx + 1) * 600)
    })
  }, [scanPhase])

  // Restart loop
  useEffect(() => {
    if (scanPhase !== 'done') return
    const timer = setTimeout(() => {
      setDisplayedLines([])
      setCurrentLine(0)
      setCurrentChar(0)
      setVisibleIssues([])
      setScanPhase('typing')
    }, 4000)
    return () => clearTimeout(timer)
  }, [scanPhase])

  return (
    <div className="w-full max-w-lg">
      {/* Mac-style terminal */}
      <div className="rounded-xl border border-border/50 bg-black/40 backdrop-blur-sm overflow-hidden shadow-2xl">
        {/* Title bar */}
        <div className="flex items-center gap-2 px-4 py-2.5 bg-white/5 border-b border-white/10">
          <div className="flex gap-1.5">
            <div className="h-3 w-3 rounded-full bg-red-500/80" />
            <div className="h-3 w-3 rounded-full bg-yellow-500/80" />
            <div className="h-3 w-3 rounded-full bg-green-500/80" />
          </div>
          <span className="text-[11px] text-white/40 ml-2 font-mono">analysis_demo.py</span>
          {scanPhase === 'scanning' && (
            <span className="ml-auto text-[10px] text-primary animate-pulse font-mono">⟳ Scanning...</span>
          )}
          {scanPhase === 'done' && (
            <span className="ml-auto text-[10px] text-red-400 font-mono">● 3 issues found</span>
          )}
        </div>

        {/* Code area */}
        <div className="p-4 font-mono text-[12px] leading-relaxed min-h-[220px] relative">
          {displayedLines.map((line, idx) => {
            const hasIssue = visibleIssues.some((i) => issueAnnotations[i].line === idx)
            return (
              <div key={idx} className="flex items-start gap-3 group">
                <span className="text-white/20 text-[10px] w-4 text-right select-none shrink-0 pt-0.5">
                  {idx + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <span className={`${hasIssue ? 'bg-red-500/15 border-b border-red-500/40' : ''} ${codeLines[idx]?.issue ? 'text-white/90' : 'text-white/60'}`}>
                    {line}
                  </span>
                </div>
              </div>
            )
          })}
          {/* Cursor blink */}
          {scanPhase === 'typing' && (
            <span className="inline-block w-2 h-4 bg-primary/80 animate-pulse ml-8" />
          )}
        </div>
      </div>

      {/* Issue annotations that slide in */}
      <div className="mt-4 space-y-2">
        {visibleIssues.map((idx) => {
          const issue = issueAnnotations[idx]
          return (
            <div
              key={idx}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border/50 bg-card/60 backdrop-blur-sm animate-in slide-in-from-left-4 duration-300"
            >
              <span
                className="text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider"
                style={{ backgroundColor: `${issue.color}20`, color: issue.color }}
              >
                {issue.severity}
              </span>
              <span className="text-xs text-foreground/80">{issue.msg}</span>
              <span className="ml-auto text-[10px] text-muted-foreground">L{issue.line + 1}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Login Form ─────────────────────────────────────────────────────────

export function Login() {
  const [isRegister, setIsRegister] = useState(false)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const { login, register } = useAuth() as any
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')
    try {
      if (isRegister) {
        await register(username, email, password)
        navigate('/')
      } else {
        await login(username, password)
        navigate('/')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Authentication failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left side - Animated Splash */}
      <div className="hidden lg:flex w-1/2 bg-secondary/30 relative flex-col items-start justify-center p-16 overflow-hidden">
        <div className="absolute inset-0 pattern-dots opacity-10" style={{ backgroundSize: '24px 24px', backgroundImage: 'radial-gradient(circle, currentColor 1px, transparent 1px)' }} />
        <div className="absolute -left-20 top-20 h-72 w-72 bg-primary/20 blur-[100px] rounded-full mix-blend-screen animate-pulse" style={{ animationDuration: '4s' }} />
        <div className="absolute -right-20 bottom-20 h-72 w-72 bg-purple-500/20 blur-[100px] rounded-full mix-blend-screen animate-pulse" style={{ animationDuration: '6s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-96 w-96 bg-indigo-500/10 blur-[120px] rounded-full" />

        <div className="relative z-10 space-y-8 animate-in fade-in slide-in-from-left-8 duration-700">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-xl bg-primary flex items-center justify-center text-primary-foreground font-bold shadow-lg shadow-primary/30">
              <Code className="h-6 w-6" />
            </div>
            <span className="font-bold text-3xl tracking-tight text-foreground">IntelliReview</span>
          </div>
          
          <div className="space-y-4 max-w-lg">
            <h1 className="text-5xl font-extrabold tracking-tight text-foreground leading-[1.1]">
              The Quality Gate for <br/><span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-purple-500">AI-Generated Code.</span>
            </h1>
            <p className="text-lg text-muted-foreground leading-relaxed">
              Watch our engine detect vulnerabilities in real-time.
            </p>
          </div>

          {/* Live typewriter demo replaces the static feature cards */}
          <TypewriterDemo />

          {/* Stats row */}
          <div className="flex gap-6 pt-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <ShieldCheck className="h-4 w-4 text-green-500" />
              <span><strong className="text-foreground">8</strong> CWEs detected</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Zap className="h-4 w-4 text-yellow-500" />
              <span><strong className="text-foreground">&lt;2s</strong> analysis time</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Activity className="h-4 w-4 text-primary" />
              <span><strong className="text-foreground">0.88</strong> confidence</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right side - Auth Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-card border-l border-border relative z-20">
        <div className="w-full max-w-sm space-y-8 animate-in fade-in slide-in-from-right-8 duration-500">
          <div className="space-y-2 text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground">
              {isRegister ? 'Create an account' : 'Welcome back'}
            </h2>
            <p className="text-muted-foreground">
              {isRegister 
                ? 'Enter your details below to create your account'
                : 'Enter your credentials to access your dashboard'}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md text-destructive text-sm text-center">
                {error}
              </div>
            )}
            
            <div className="space-y-2">
              <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-foreground">
                Username
              </label>
              <input
                type="text"
                required
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-shadow"
                placeholder="developer01"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            
            {isRegister && (
              <div className="space-y-2 animate-in slide-in-from-top-2 duration-300">
                <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-foreground">
                  Email
                </label>
                <input
                  type="email"
                  required
                  className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-shadow"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            )}
            
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-foreground">
                  Password
                </label>
                {!isRegister && (
                  <button type="button" className="text-xs font-medium text-primary hover:text-primary/90 underline-offset-4 hover:underline transition-all">
                    Forgot details?
                  </button>
                )}
              </div>
              <input
                type="password"
                required
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-shadow"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <button
              disabled={isLoading}
              type="submit"
              className="w-full inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 group mt-2"
            >
              {isLoading ? (
                 <div className="h-4 w-4 rounded-full border-2 border-primary-foreground border-t-transparent animate-spin" />
              ) : (
                <>
                  {isRegister ? 'Sign Up' : 'Sign In'}
                  <ArrowRight className="ml-2 h-4 w-4 opacity-70 group-hover:translate-x-1 group-hover:opacity-100 transition-all" />
                </>
              )}
            </button>
          </form>


          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">
                Or continue with
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <button
              type="button"
              onClick={() => window.location.href = '/auth/github/login'}
              className="w-full inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-black text-white hover:bg-gray-900 h-10 px-4 py-2 gap-2 border border-border"
            >
              <svg width="20" height="20" fill="currentColor" viewBox="0 0 24 24" className="mr-2"><path d="M12 0C5.37 0 0 5.373 0 12c0 5.303 3.438 9.8 8.205 11.387.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.726-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.09-.745.083-.729.083-.729 1.205.085 1.84 1.237 1.84 1.237 1.07 1.834 2.807 1.304 3.492.997.108-.775.418-1.305.762-1.605-2.665-.305-5.466-1.334-5.466-5.931 0-1.31.468-2.381 1.236-3.221-.124-.303-.535-1.523.117-3.176 0 0 1.008-.322 3.3 1.23.957-.266 1.984-.399 3.003-.404 1.018.005 2.046.138 3.006.404 2.289-1.553 3.295-1.23 3.295-1.23.653 1.653.242 2.873.119 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.804 5.624-5.475 5.921.43.372.823 1.104.823 2.222 0 1.606-.014 2.898-.014 3.293 0 .322.216.694.825.576C20.565 21.796 24 17.299 24 12c0-6.627-5.373-12-12-12z"/></svg>
              Continue with GitHub
            </button>
          </div>

          <div className="text-center">
            <p className="text-sm text-muted-foreground">
              {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
              <button
                type="button"
                onClick={() => setIsRegister(!isRegister)}
                className="font-semibold text-primary hover:text-primary/90 hover:underline transition-all"
              >
                {isRegister ? 'Sign in' : 'Sign up'}
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
