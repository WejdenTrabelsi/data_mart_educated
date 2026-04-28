import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { BarChart3, Sparkles, Menu, X } from 'lucide-react';

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div className={`bg-white shadow-2xl h-screen transition-all duration-300 flex flex-col ${collapsed ? 'w-16' : 'w-64'}`}>
      <div className="p-4 border-b flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-primary rounded-2xl flex items-center justify-center text-white font-bold text-xl">SP</div>
          {!collapsed && <span className="font-bold text-2xl text-primary">Admin</span>}
        </div>
        <button onClick={() => setCollapsed(!collapsed)} className="text-gray-500 hover:text-primary">
          {collapsed ? <Menu size={24} /> : <X size={24} />}
        </button>
      </div>

      <div className="flex-1 p-3 space-y-1">
        <button
          onClick={() => navigate('/dashboard')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-left ${location.pathname === '/dashboard' ? 'bg-primary text-white' : 'hover:bg-gray-100'}`}
        >
          <BarChart3 size={20} />
          {!collapsed && <span>Tableau de bord</span>}
        </button>

        <button
          onClick={() => navigate('/suggestions')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-left ${location.pathname === '/suggestions' ? 'bg-primary text-white' : 'hover:bg-gray-100'}`}
        >
          <Sparkles size={20} />
          {!collapsed && <span>Suggestions IA</span>}
        </button>
      </div>

      <div className="p-4 border-t text-xs text-gray-400 text-center">
        {!collapsed && 'Lycée • 2026'}
      </div>
    </div>
  );
}