import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth, UserRole } from '@/contexts/AuthContext';

interface ProtectedRouteProps {
  allowedRoles?: UserRole[];
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-muted-foreground animate-pulse">Loading Identity...</div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    // To allow unauthenticated users to use mock login, we just render if they are on dashboard
    // But in a real scenario we'd navigate to a /login route.
    // For now we will allow rendering if no user, but strictly enforce if allowedRoles is provided!
    if (allowedRoles && allowedRoles.length > 0) {
      return <Navigate to="/" replace />;
    }
    return <Outlet />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
