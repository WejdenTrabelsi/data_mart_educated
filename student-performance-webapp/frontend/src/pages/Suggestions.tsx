import { useState, useEffect } from "react";
import axios from "axios";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";

type Suggestion = {
  category: string;
  title: string;
  description: string;
  priority: "high" | "medium" | "low";
};

const priorityBadge: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-emerald-100 text-emerald-700",
};

const categoryEmoji: Record<string, string> = {
  performance: "🎓",
  attendance: "👥",
  general: "📊",
};

export default function Suggestions() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const API_URL = import.meta.env.VITE_API_URL;
  const token = localStorage.getItem("token");

  const fetchSuggestions = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await axios.post(
        `${API_URL}/suggestions/generate`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSuggestions(res.data.suggestions || []);
    } catch {
      setError("Erreur lors de la génération des suggestions.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSuggestions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex min-h-screen bg-[#F5F4FF]">
      <Sidebar />
      <div className="flex-1">
        <Navbar />
        <div className="p-8 max-w-4xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-3xl font-bold text-primary mb-1">Suggestions IA</h1>
              <p className="text-gray-600">
                Recommandations générées à partir de l'analyse de vos données actuelles.
              </p>
            </div>
            <button
              onClick={fetchSuggestions}
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 bg-primary text-white rounded-xl font-medium hover:bg-primary/90 disabled:opacity-50 transition"
            >
              <span className={loading ? "animate-spin inline-block" : ""}>↻</span>
              Régénérer
            </button>
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6 text-sm">
              {error}
            </div>
          )}

          {loading && suggestions.length === 0 && (
            <div className="flex flex-col items-center justify-center h-64 gap-3">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary" />
              <p className="text-gray-500 text-sm">L'IA analyse vos données…</p>
            </div>
          )}

          <div className="space-y-4">
            {suggestions.map((s, idx) => (
              <div
                key={idx}
                className="flex gap-4 p-5 bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition"
              >
                <div className="flex-shrink-0 w-12 h-12 flex items-center justify-center rounded-lg bg-[#F5F4FF] text-2xl">
                  {categoryEmoji[s.category] || "💡"}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <h3 className="font-bold text-gray-900">{s.title}</h3>
                    <span
                      className={`text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full ${
                        priorityBadge[s.priority] || priorityBadge.medium
                      }`}
                    >
                      {s.priority}
                    </span>
                  </div>
                  <p className="text-gray-600 text-sm leading-relaxed">{s.description}</p>
                  <span className="inline-block mt-2 text-[10px] font-semibold text-gray-400 uppercase tracking-wide">
                    {s.category}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {!loading && suggestions.length === 0 && !error && (
            <div className="text-center text-gray-400 mt-20">
              Aucune suggestion pour le moment.<br />
              Cliquez sur <strong>Régénérer</strong> pour lancer l'analyse.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}