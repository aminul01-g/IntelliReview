import React, { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import * as LucideIcons from 'lucide-react'

const {
  Search, LayoutDashboard, FileCode, History, Activity, User,
  UploadCloud, Code, Shield, Settings, ArrowRight, Command,
} = LucideIcons as any
const FlaskConical = (LucideIcons as any).FlaskConical || Activity

interface CommandItem {
  id: string
  label: string
  description?: string
  icon: any
  action: () => void
  category: string
  keywords?: string[]
}

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  const items: CommandItem[] = useMemo(() => [
    { id: 'dashboard', label: 'Dashboard', description: 'Command Center overview', icon: LayoutDashboard, action: () => navigate('/'), category: 'Navigation', keywords: ['home', 'main', 'overview'] },
    { id: 'upload', label: 'Upload Project', description: 'Upload code for analysis', icon: UploadCloud, action: () => navigate('/upload'), category: 'Navigation', keywords: ['project', 'file', 'zip'] },
    { id: 'review', label: 'Review Engine', description: 'Analyze code or diffs', icon: FileCode, action: () => navigate('/review'), category: 'Navigation', keywords: ['analyze', 'code', 'diff', 'scan'] },
    { id: 'rules', label: 'Rules Studio', description: 'Custom rule management', icon: Code, action: () => navigate('/rules'), category: 'Navigation', keywords: ['custom', 'regex', 'pattern'] },
    { id: 'metrics', label: 'Analytics & Metrics', description: 'Team velocity and AI performance', icon: Activity, action: () => navigate('/metrics'), category: 'Navigation', keywords: ['charts', 'velocity', 'stats'] },
    { id: 'research', label: 'Research Dashboard', description: 'Thesis-grade visualizations', icon: FlaskConical, action: () => navigate('/research'), category: 'Navigation', keywords: ['threshold', 'ablation', 'confidence'] },
    { id: 'history', label: 'Scan History', description: 'Past analysis results', icon: History, action: () => navigate('/history'), category: 'Navigation', keywords: ['past', 'scans', 'results'] },
    { id: 'profile', label: 'Profile Settings', description: 'Account and API keys', icon: User, action: () => navigate('/profile'), category: 'Navigation', keywords: ['account', 'settings', 'api'] },
    { id: 'admin-policies', label: 'Admin Policies', description: 'Manage enforcement policies', icon: Shield, action: () => navigate('/admin/policies'), category: 'Admin', keywords: ['policy', 'admin', 'rules'] },
    { id: 'admin-health', label: 'Admin Health', description: 'System health dashboard', icon: Settings, action: () => navigate('/admin/health'), category: 'Admin', keywords: ['health', 'system', 'status'] },
    { id: 'new-scan', label: 'New Code Scan', description: 'Quick-start a code analysis', icon: FileCode, action: () => navigate('/review'), category: 'Actions', keywords: ['new', 'quick', 'start', 'analyze'] },
    { id: 'upload-project', label: 'Upload New Project', description: 'Start a new project upload', icon: UploadCloud, action: () => navigate('/upload'), category: 'Actions', keywords: ['new', 'project', 'create'] },
  ], [navigate])

  // Filter items by query
  const filtered = useMemo(() => {
    if (!query.trim()) return items
    const q = query.toLowerCase()
    return items.filter((item) => {
      return (
        item.label.toLowerCase().includes(q) ||
        item.description?.toLowerCase().includes(q) ||
        item.keywords?.some((k) => k.includes(q))
      )
    })
  }, [items, query])

  // Group by category
  const grouped = useMemo(() => {
    const map: Record<string, CommandItem[]> = {}
    filtered.forEach((item) => {
      if (!map[item.category]) map[item.category] = []
      map[item.category].push(item)
    })
    return map
  }, [filtered])

  // ⌘K / Ctrl+K listener + custom event from Header search button
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen((v) => !v)
        setQuery('')
        setSelectedIndex(0)
      }
      if (e.key === 'Escape') setOpen(false)
    }
    function customHandler() {
      setOpen(true)
      setQuery('')
      setSelectedIndex(0)
    }
    window.addEventListener('keydown', handler)
    window.addEventListener('intellireview:command-palette', customHandler)
    return () => {
      window.removeEventListener('keydown', handler)
      window.removeEventListener('intellireview:command-palette', customHandler)
    }
  }, [])

  // Auto-focus input
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  // Arrow key navigation
  useEffect(() => {
    setSelectedIndex(0)
  }, [query])

  const handleKeyDown = (e: any) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      filtered[selectedIndex].action()
      setOpen(false)
    }
  }

  // Scroll selected into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-index="${selectedIndex}"]`)
    el?.scrollIntoView({ block: 'nearest' })
  }, [selectedIndex])

  if (!open) return null

  let flatIndex = -1

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]" onClick={() => setOpen(false)}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200" />

      {/* Palette */}
      <div
        className="relative w-full max-w-lg bg-card border border-border rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
          <Search className="h-5 w-5 text-muted-foreground shrink-0" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Type a command or search..."
            className="flex-1 bg-transparent outline-none text-sm text-foreground placeholder:text-muted-foreground"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <kbd className="hidden sm:inline-flex h-5 items-center gap-0.5 rounded border bg-muted px-1.5 font-mono text-[10px] text-muted-foreground">
            Esc
          </kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-[340px] overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No results found for "<span className="text-foreground font-medium">{query}</span>"
            </div>
          ) : (
            Object.entries(grouped).map(([category, categoryItems]) => (
              <div key={category}>
                <div className="px-2 py-1.5 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                  {category}
                </div>
                {categoryItems.map((item) => {
                  flatIndex++
                  const idx = flatIndex
                  return (
                    <button
                      key={item.id}
                      data-index={idx}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                        idx === selectedIndex
                          ? 'bg-primary/10 text-foreground'
                          : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
                      }`}
                      onClick={() => { item.action(); setOpen(false) }}
                      onMouseEnter={() => setSelectedIndex(idx)}
                    >
                      <item.icon className="h-4 w-4 shrink-0" />
                      <div className="flex-1 text-left">
                        <div className="font-medium text-foreground">{item.label}</div>
                        {item.description && (
                          <div className="text-xs text-muted-foreground">{item.description}</div>
                        )}
                      </div>
                      {idx === selectedIndex && <ArrowRight className="h-3 w-3 text-primary" />}
                    </button>
                  )
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-border bg-muted/30 text-[10px] text-muted-foreground">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1"><kbd className="px-1 py-0.5 rounded bg-muted border text-[9px]">↑↓</kbd> navigate</span>
            <span className="flex items-center gap-1"><kbd className="px-1 py-0.5 rounded bg-muted border text-[9px]">↵</kbd> select</span>
            <span className="flex items-center gap-1"><kbd className="px-1 py-0.5 rounded bg-muted border text-[9px]">esc</kbd> close</span>
          </div>
          <span>{filtered.length} result{filtered.length !== 1 ? 's' : ''}</span>
        </div>
      </div>
    </div>
  )
}
