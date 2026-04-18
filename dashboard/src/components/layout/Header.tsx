import React, { useState, useRef } from 'react'
import { Bell, Search, User, LogOut, Settings } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useNavigate } from 'react-router-dom'

export function Header() {
  const { user, isAuthenticated, logout, isLoading } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  // Close dropdown on outside click
  React.useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    if (menuOpen) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [menuOpen])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <header className="h-16 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50 flex items-center justify-between px-6">
      <div className="flex items-center gap-4 flex-1">
        {/* Placeholder for Breadcrumbs */}
        <div className="hidden sm:flex items-center text-sm text-muted-foreground">
          IntelliReview <span className="mx-2">/</span> <span className="text-foreground font-medium">Dashboard</span>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <button className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-md border border-border bg-muted/30 text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors w-64 justify-start">
          <Search className="h-4 w-4" />
          <span className="flex-1 text-left">Search...</span>
          <kbd className="hidden md:inline-flex h-5 items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100">
            <span className="text-xs">⌘</span>K
          </kbd>
        </button>
        <div className="flex items-center gap-2">
          <span className="flex h-2 w-2 rounded-full bg-green-500"></span>
          <span className="text-xs text-muted-foreground font-medium hidden md:inline-block">API Connected</span>
        </div>
        <div className="h-8 w-px bg-border mx-1"></div>
        <button className="relative h-8 w-8 rounded-full bg-secondary flex items-center justify-center hover:bg-secondary/80 outline-none">
          <Bell className="h-4 w-4 text-foreground" />
          <span className="absolute top-0 right-0 h-2 w-2 rounded-full bg-primary ring-2 ring-background"></span>
        </button>
        {/* User menu */}
        {!isLoading && isAuthenticated ? (
          <div className="relative" ref={menuRef}>
            <button
              className="h-8 w-8 rounded-full bg-muted flex items-center justify-center border border-border overflow-hidden cursor-pointer hover:ring-2 hover:ring-primary/40 transition"
              onClick={() => setMenuOpen((v) => !v)}
              aria-label="User menu"
            >
              <User className="h-4 w-4 text-muted-foreground" />
            </button>
            {menuOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-popover border border-border rounded-lg shadow-lg z-50 animate-in fade-in slide-in-from-top-2 duration-200">
                <div className="px-4 py-3 border-b border-border">
                  <div className="font-semibold text-sm text-foreground">{user?.name || user?.email}</div>
                  <div className="text-xs text-muted-foreground">{user?.email}</div>
                </div>
                <button
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm hover:bg-muted/40 transition-colors text-foreground"
                  onClick={() => { setMenuOpen(false); navigate('/profile') }}
                >
                  <Settings className="h-4 w-4" /> Profile & Settings
                </button>
                <button
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm hover:bg-destructive/10 text-destructive border-t border-border transition-colors"
                  onClick={handleLogout}
                >
                  <LogOut className="h-4 w-4" /> Logout
                </button>
              </div>
            )}
          </div>
        ) : (
          <button
            className="h-8 px-4 rounded-md bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition"
            onClick={() => navigate('/login')}
          >
            Login
          </button>
        )}
      </div>
    </header>
  )
}
