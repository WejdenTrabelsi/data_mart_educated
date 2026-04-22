// frontend/src/pages/Dashboard.tsx
import DirectorSidebar from '../components/DirectorSideBar';
import Navbar from '../components/Navbar';
import ChatWidget from "../components/ChatWidget";

export default function Dashboard() {
  const role = localStorage.getItem('user_role');
  const fullName = localStorage.getItem('full_name');

  // Your public embed URL (the one that works)
  const PUBLIC_EMBED_URL = "http://localhost:3000/public/dashboard/a39c76e7-e1d1-4e95-9931-ee50aefe59cd";

  return (
    <div className="flex min-h-screen bg-[#F5F4FF]">
      {/* Sidebar */}
      <DirectorSidebar />

      {/* Main content area */}
      <div className="flex-1">
        <Navbar />

        <div className="p-8">
          <h1 className="text-4xl font-bold text-primary mb-2">
            Bienvenue, {fullName} 👋
          </h1>
          <p className="text-lg text-gray-600 mb-8">
            Tableau de bord complet - Tous les élèves
          </p>

          {/* Metabase Dashboard */}
          <div 
            className="bg-white rounded-3xl shadow-xl overflow-hidden" 
            style={{ height: '700px' }}
          >
            <iframe
              src={PUBLIC_EMBED_URL}
              width="100%"
              height="100%"
              frameBorder="0"
              allowFullScreen
              className="w-full h-full"
              title="Metabase Dashboard"
            />
          </div>
        </div>
      </div>

      {/* NEW: Floating Chat Widget (appears on top of everything) */}
      <ChatWidget />
    </div>
  );
}