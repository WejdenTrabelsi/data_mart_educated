import { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Users, CheckCircle, MessageSquare } from 'lucide-react';
import DirectorSidebar from '../components/DirectorSideBar';
export default function AdminPanel() {
  const [pending, setPending] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    axios.get(`${import.meta.env.VITE_API_URL}/parent/pending`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(res => setPending(res.data))
      .catch(() => navigate('/dashboard'))
      .finally(() => setLoading(false));
  }, [navigate]);

  const approve = async (userId: number, remarks: string) => {
    const token = localStorage.getItem('token');
    await axios.post(`${import.meta.env.VITE_API_URL}/parent/approve/${userId}`, 
      { remarks }, 
      { headers: { Authorization: `Bearer ${token}` } }
    );
    setPending(pending.filter(p => p.user_id !== userId));
  };

  if (loading) return <div className="p-8 text-center text-xl">Chargement...</div>;

  return (
    <div className="flex min-h-screen bg-[#F5F4FF]">
    <DirectorSidebar />
    
    <div className="flex min-h-screen bg-[#F5F4FF]">
      {/* LEFT SIDEBAR MENU */}
      
      <div className="w-64 bg-white shadow-xl p-6">
        <div className="flex items-center gap-3 mb-10">
          <div className="w-9 h-9 bg-primary rounded-2xl flex items-center justify-center text-white font-bold">SP</div>
          <h2 className="text-2xl font-bold text-primary">Directeur</h2>
        </div>

        <nav className="space-y-2">
          <a href="/admin" className="flex items-center gap-3 px-4 py-3 bg-primary text-white rounded-2xl">
            <Users size={20} />
            Demandes parents
          </a>
          <a href="/dashboard" className="flex items-center gap-3 px-4 py-3 text-gray-600 hover:bg-gray-100 rounded-2xl">
            📊 Tableau de bord
          </a>
        </nav>
      </div>

      {/* MAIN CONTENT */}
      <div className="flex-1 p-8">
        <h1 className="text-4xl font-bold text-primary mb-8">Demandes d'inscription parents</h1>

        {pending.length === 0 ? (
          <p className="text-xl text-gray-500">Aucune demande en attente.</p>
        ) : (
          <div className="space-y-6">
            {pending.map((parent) => (
              <div key={parent.user_id} className="bg-white rounded-3xl shadow-xl p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-semibold text-xl">{parent.full_name}</p>
                    <p className="text-gray-500">{parent.email}</p>
                    <p className="text-sm text-gray-400 mt-1">
                      Enfant ID : <span className="font-medium">{parent.student_natural_key}</span>
                    </p>
                  </div>
                </div>

                {/* Remarks textarea */}
                <div className="mt-6">
                  <label className="flex items-center gap-2 text-sm font-medium mb-2 text-gray-600">
                    <MessageSquare size={16} />
                    Remarque / Commentaire (visible par le parent)
                  </label>
                  <textarea
                    id={`remarks-${parent.user_id}`}
                    rows={3}
                    className="w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:border-primary resize-none"
                    placeholder="Ex: Enfant en 3ème année Sciences - Très bon dossier"
                  />
                </div>

                <button
                  onClick={() => {
                    const remarks = (document.getElementById(`remarks-${parent.user_id}`) as HTMLTextAreaElement).value;
                    approve(parent.user_id, remarks);
                  }}
                  className="mt-6 w-full bg-green-600 hover:bg-green-700 text-white py-4 rounded-2xl font-semibold flex items-center justify-center gap-2"
                >
                  <CheckCircle size={20} />
                  Approuver la demande
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
    </div>
  );
}