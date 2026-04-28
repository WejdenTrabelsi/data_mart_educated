import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';

export default function Suggestions() {
  return (
    <div className="flex min-h-screen bg-[#F5F4FF]">
      <Sidebar />
      <div className="flex-1">
        <Navbar />
        <div className="p-8">
          <h1 className="text-3xl font-bold text-primary mb-4">Suggestions IA</h1>
          <p className="text-gray-600">Cette page affichera les recommandations générées par l'IA.</p>
        </div>
      </div>
    </div>
  );
}