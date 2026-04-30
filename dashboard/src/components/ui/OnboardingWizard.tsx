import React, { useState } from 'react'
import { Zap, Code, BarChart3, ArrowRight, Play, CheckCircle, Shield, GitBranch } from 'lucide-react'

interface OnboardingWizardProps {
  onDismiss: () => void
  onTryReview: () => void
}

const VULNERABLE_CODE = `def authenticate(username, password):
    query = "SELECT * FROM users WHERE name = '" + username + "'"
    result = eval(query)
    api_key = "sk-proj-8x9f2k3m1n"
    return result`

const steps = [
  {
    icon: Zap,
    title: 'Welcome to IntelliReview',
    subtitle: 'AI-Powered Code Review Intelligence',
    description: 'IntelliReview uses multi-agent AI to detect security vulnerabilities, anti-patterns, and technical debt in your code — before they reach production.',
    features: [
      { icon: Shield, text: 'Security scanning with CWE references' },
      { icon: Code, text: 'AST-level complexity analysis' },
      { icon: BarChart3, text: 'Longitudinal metrics & learning' },
      { icon: GitBranch, text: 'GitHub PR webhook integration' },
    ]
  },
  {
    icon: Code,
    title: 'Try It Now',
    subtitle: 'Paste code and see issues found instantly',
    description: 'The Review Engine auto-detects Python, JavaScript, Java, and C++. Try it with this vulnerable code sample:',
    code: VULNERABLE_CODE,
  },
  {
    icon: BarChart3,
    title: 'Track Your Progress',
    subtitle: 'Every review makes the system smarter',
    description: 'Accept or reject suggestions to fine-tune the AI. View your team\'s velocity, severity trends, and false positive reduction trajectory on the Metrics page.',
  }
]

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({ onDismiss, onTryReview }) => {
  const [currentStep, setCurrentStep] = useState(0)
  const step = steps[currentStep]
  const StepIcon = step.icon

  return (
    <div className="border border-primary/20 rounded-2xl bg-gradient-to-br from-primary/5 via-card to-card p-8 shadow-lg relative overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-48 h-48 bg-primary/3 rounded-full blur-2xl translate-y-1/2 -translate-x-1/2 pointer-events-none" />

      {/* Step indicators */}
      <div className="flex items-center gap-2 mb-6 relative">
        {steps.map((_, idx) => (
          <button
            key={idx}
            onClick={() => setCurrentStep(idx)}
            className={`h-1.5 rounded-full transition-all duration-300 ${
              idx === currentStep
                ? 'w-8 bg-primary'
                : idx < currentStep
                ? 'w-4 bg-primary/40'
                : 'w-4 bg-muted-foreground/20'
            }`}
          />
        ))}
        <button
          onClick={onDismiss}
          className="ml-auto text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Skip setup
        </button>
      </div>

      {/* Content */}
      <div className="relative flex flex-col lg:flex-row gap-8 items-start">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center border border-primary/20">
              <StepIcon className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-foreground">{step.title}</h2>
              <p className="text-sm text-primary font-medium">{step.subtitle}</p>
            </div>
          </div>

          <p className="text-muted-foreground leading-relaxed mb-6 max-w-lg">{step.description}</p>

          {/* Step 1: Features grid */}
          {currentStep === 0 && step.features && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
              {step.features.map((feature, idx) => {
                const FeatureIcon = feature.icon
                return (
                  <div
                    key={idx}
                    className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 border border-border/50 hover:bg-muted/50 transition-colors"
                  >
                    <FeatureIcon className="h-4 w-4 text-primary flex-shrink-0" />
                    <span className="text-sm text-foreground">{feature.text}</span>
                  </div>
                )
              })}
            </div>
          )}

          {/* Step 2: Code sample */}
          {currentStep === 1 && step.code && (
            <div className="mb-6">
              <div className="bg-background border border-border rounded-lg overflow-hidden">
                <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-muted/30">
                  <div className="flex gap-1.5">
                    <div className="h-2.5 w-2.5 rounded-full bg-red-500/60" />
                    <div className="h-2.5 w-2.5 rounded-full bg-yellow-500/60" />
                    <div className="h-2.5 w-2.5 rounded-full bg-green-500/60" />
                  </div>
                  <span className="text-xs text-muted-foreground font-mono ml-2">vulnerable_example.py</span>
                </div>
                <pre className="p-4 text-sm font-mono text-foreground/90 overflow-x-auto leading-relaxed">
                  {step.code}
                </pre>
              </div>
              <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                <Shield className="h-3.5 w-3.5 text-destructive" />
                <span>Contains: SQL injection, eval() usage, hardcoded API key</span>
              </div>
            </div>
          )}

          {/* Step 3: Completion */}
          {currentStep === 2 && (
            <div className="flex flex-col gap-3 mb-6">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0" />
                <span className="text-sm text-foreground">Your dashboard tracks all analyses automatically</span>
              </div>
              <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                <BarChart3 className="h-5 w-5 text-blue-500 flex-shrink-0" />
                <span className="text-sm text-foreground">The AI learns from your accept/reject feedback</span>
              </div>
            </div>
          )}

          {/* Navigation buttons */}
          <div className="flex items-center gap-3">
            {currentStep > 0 && (
              <button
                onClick={() => setCurrentStep(s => s - 1)}
                className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground border border-border rounded-lg transition-colors"
              >
                Back
              </button>
            )}
            {currentStep < steps.length - 1 ? (
              <button
                onClick={() => setCurrentStep(s => s + 1)}
                className="px-5 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-semibold flex items-center gap-2 hover:bg-primary/90 transition-colors shadow-sm"
              >
                Continue <ArrowRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                onClick={onTryReview}
                className="px-5 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-semibold flex items-center gap-2 hover:bg-primary/90 transition-colors shadow-sm"
              >
                <Play className="h-4 w-4 fill-current" /> Try the Review Engine
              </button>
            )}
            {currentStep === 1 && (
              <button
                onClick={onTryReview}
                className="px-4 py-2 text-sm font-medium text-primary hover:text-primary/80 border border-primary/30 rounded-lg transition-colors flex items-center gap-2"
              >
                <Play className="h-3.5 w-3.5 fill-current" /> Try this code now
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
