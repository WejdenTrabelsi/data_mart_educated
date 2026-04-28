import { useNavigate } from 'react-router-dom';
import { LogOut, User } from 'lucide-react';

export default function Navbar() {
  const navigate = useNavigate();
  const fullName = localStorage.getItem('full_name');

  const handleLogout = () => {
    localStorage.clear();
    navigate('/');
  };

  return (
    <nav className="bg-white border-b shadow-sm px-8 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="bg-primary text-white px-4 py-2 rounded-2xl font-bold">SP</div>
        <div>
          <h1 className="font-semibold text-xl">Performance Scolaire</h1>
          <p className="text-xs text-gray-500 -mt-1">Lycée • Tableau de bord</p>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <User size={20} className="text-primary" />
          <div>
            <p className="font-medium text-sm">{fullName}</p>
            <p className="text-xs text-gray-500">Administrateur</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 text-red-600 hover:text-red-700"
        >
          <LogOut size={20} />
          Déconnexion
        </button>
      </div>
    </nav>
  );
}