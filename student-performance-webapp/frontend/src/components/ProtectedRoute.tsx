// ---------------------------------------------------------------------------
// PROTECTEDROUTE.TSX  --  Authentication Guard Component
// ---------------------------------------------------------------------------
// This component wraps any page that should be private (Dashboard, etc.).
// It checks the browser's localStorage for a token.
// If missing, it redirects to the login page immediately.
// If present, it renders the child content normally.
// ---------------------------------------------------------------------------

// Navigate is a React Router component that triggers an instant redirect.
import { Navigate } from 'react-router-dom';

// ReactNode is the TypeScript type for anything React can render:
// JSX elements, strings, numbers, arrays, etc.
import type { ReactNode } from 'react';

// ---------------------------------------------------------------------------
// Props interface (implicit via destructuring):
//   children: whatever JSX is placed INSIDE <ProtectedRoute>...</ProtectedRoute>
// ---------------------------------------------------------------------------
export default function ProtectedRoute({ children }: { children: ReactNode }) {
  
  // -------------------------------------------------------------------------
  // Read the token from browser localStorage.
  // localStorage is a simple key-value store that persists even if the user
  // closes the browser tab. It is scoped to the current domain.
  // -------------------------------------------------------------------------
  const token = localStorage.getItem('token');
  
  // -------------------------------------------------------------------------
  // GUARD CLAUSE
  // If token is null or undefined, return Navigate which instantly changes
  // the URL to "/" (the login page). replace=true means the current URL is
  // replaced in history, so the back button won't return to the blocked page.
  // -------------------------------------------------------------------------
  if (!token) return <Navigate to="/" replace />;
  
  // -------------------------------------------------------------------------
  // If we reach here, the token exists. Render the wrapped children.
  // The fragment <>{children}</> is needed because a component must return
  // a single root element, and children might be an array.
  // -------------------------------------------------------------------------
  return <>{children}</>;
}