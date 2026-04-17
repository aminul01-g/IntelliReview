import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Code, ArrowRight, ShieldCheck, Zap } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

export function Login() {
  const [isRegister, setIsRegister] = useState(false)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')
    try {
      // For now, mock the login process with the existing context functionality
      // In production this would hit real endpoints, but we use the context's mocked login
      if (isRegister) {
        // Mock register logic -> just log them in
        login()
        navigate('/')
      } else {
        login()
        navigate('/')
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left side - Dynamic Splash Screen */}
      <div className="hidden lg:flex w-1/2 bg-secondary/30 relative flex-col items-start justify-center p-16 overflow-hidden">
        <div className="absolute inset-0 pattern-dots opacity-10" style={{ backgroundSize: '24px 24px', backgroundImage: 'radial-gradient(circle, currentColor 1px, transparent 1px)' }} />
        <div className="absolute -left-20 top-20 h-72 w-72 bg-primary/20 blur-[100px] rounded-full mix-blend-screen" />
        <div className="absolute -right-20 bottom-20 h-72 w-72 bg-purple-500/20 blur-[100px] rounded-full mix-blend-screen" />

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
            <p className="text-xl text-muted-foreground leading-relaxed">
              Elevate your codebase. Our deterministic and generative multi-agent platform reviews PRs natively, tracking architectural degradation effortlessly.
            </p>
          </div>

          <div className="flex flex-col gap-4 pt-8">
             <div className="flex items-center gap-3 bg-card/40 backdrop-blur-sm border border-border/50 p-4 rounded-xl">
               <ShieldCheck className="h-6 w-6 text-green-500" />
               <div className="flex flex-col">
                 <span className="font-semibold text-sm">Deterministic Security</span>
                 <span className="text-muted-foreground text-xs">CWE and OWASP compliant flaw detection</span>
               </div>
             </div>
             <div className="flex items-center gap-3 bg-card/40 backdrop-blur-sm border border-border/50 p-4 rounded-xl">
               <Zap className="h-6 w-6 text-yellow-500" />
               <div className="flex flex-col">
                 <span className="font-semibold text-sm">Real-time Performance Analysis</span>
                 <span className="text-muted-foreground text-xs">Instantly detects O(n²) bottlenecks</span>
               </div>
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
