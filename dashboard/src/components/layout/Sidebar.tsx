
import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
// @ts-ignore – lucide-react v0.562 barrel exports resolve correctly at Vite runtime
import { LayoutDashboard, History, FileCode, Code, Settings, UploadCloud, Activity, User, Shield, FolderOpen } from 'lucide-react'
import * as LucideAll from 'lucide-react'
const FlaskConical = (LucideAll as any).FlaskConical || Activity
import { cn } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'


const navItems = [
  { name: 'Dashboard', to: '/', icon: LayoutDashboard },
  { name: 'My Projects', to: '/projects', icon: FolderOpen },
  { name: 'Upload Project', to: '/upload', icon: UploadCloud },
  { name: 'Review Engine', to: '/review', icon: FileCode },
  { name: 'Rules Studio', to: '/rules', icon: Code },
  { name: 'Metrics', to: '/metrics', icon: Activity },
  { name: 'Research', to: '/research', icon: FlaskConical },
  { name: 'Scan History', to: '/history', icon: History },
  { name: 'Profile', to: '/profile', icon: User },
]

export function Sidebar() {
  const { user } = useAuth();
  const navigate = useNavigate();
  return (
    <aside className="w-64 border-r border-border bg-card flex flex-col hidden md:flex h-screen sticky top-0">
      <div className="h-16 flex items-center px-6 border-b border-border">
        <div className="flex items-center gap-2">
           <div className="h-8 w-8 rounded-md bg-primary flex items-center justify-center text-primary-foreground font-bold">
             IR
           </div>
           <span className="font-bold text-lg tracking-tight">IntelliReview</span>
        </div>
      </div>
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }: any) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive 
                  ? "bg-secondary text-secondary-foreground" 
                  : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.name}
          </NavLink>
        ))}

        {/* Admin & Reviewer: Policy Manager */}
        {(user?.role === 'Admin' || user?.role === 'Reviewer') && (
          <NavLink
            to="/admin/policies"
            className={({ isActive }: any) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive 
                  ? "bg-secondary text-secondary-foreground" 
                  : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
              )
            }
          >
            <Shield className="h-4 w-4" />
            {user?.role === 'Admin' ? 'Policy Manager' : 'Team Policies'}
          </NavLink>
        )}

        {/* Admin only: Health Dashboard */}
        {user?.role === 'Admin' && (
          <NavLink
            to="/admin/health"
            className={({ isActive }: any) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive 
                  ? "bg-secondary text-secondary-foreground" 
                  : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
              )
            }
          >
            <Shield className="h-4 w-4 rotate-45" />
            Admin Health
          </NavLink>
        )}
      </nav>
      <div className="p-4 border-t border-border">
        <button className="flex w-full items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-muted-foreground hover:bg-secondary/50 hover:text-foreground transition-colors">
          <Settings className="h-4 w-4" />
          Settings
        </button>
      </div>
    </aside>
  )
}
