import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './components/Login';
import Dashboard from './pages/Dashboard';
import Suggestions from './pages/Suggestions';
import ProtectedRoute from './components/ProtectedRoute';

import './index.css';

function App() {
  return (
    <Router>
      <Routes>
        {/*the login is a public route the rest are Protected routes (private)       */}
        <Route path="/" element={<Login />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/suggestions" element={<ProtectedRoute><Suggestions /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
        {/* the "*"  (anything else) redirects to / */}
      </Routes>
    </Router>
  );
}

export default App;