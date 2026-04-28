import { useState, useEffect } from "react";
import axios from "axios";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar, Line, Doughnut } from "react-chartjs-2";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";
import ChatWidget from "../components/ChatWidget";
import KPICard from "../components/KPICard";
import ChartCard from "../components/ChartCard";
import FilterBar from "../components/FilterBar";

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

type TabKey = "global" | "attendance";

// Chart colors
const COLORS = {
  primary: "#6366f1", secondary: "#8b5cf6", success: "#22c55e",
  warning: "#f59e0b", danger: "#ef4444", info: "#3b82f6",
  purple: "#a855f7", pink: "#ec4899", teal: "#14b8a6", orange: "#f97316",
};

// =========================================================
// PERFORMANCE FILTER CONFIG
// optionsKey maps to the plural key returned by filter_options
// =========================================================
const PERF_FILTER_CONFIG = [
  { key: "branch",   label: "Filière",  optionsKey: "branches"  },
  { key: "level",    label: "Niveau",   optionsKey: "levels"    },
  { key: "semester", label: "Semestre", optionsKey: "semesters" },
  { key: "year",     label: "Année",    optionsKey: "years"     },
];

// =========================================================
// ATTENDANCE FILTER CONFIG
// optionsKey maps to the plural key returned by filter_options
// =========================================================
const ATT_FILTER_CONFIG = [
  { key: "day",      label: "Jour",     optionsKey: "days"      },
  { key: "month",    label: "Mois",     optionsKey: "months"    },
  { key: "semester", label: "Semestre", optionsKey: "semesters" },
  { key: "year",     label: "Année",    optionsKey: "years"     },
  { key: "zone",     label: "Zone",     optionsKey: "zones"     },
];

export default function Dashboard() {
  const fullName = localStorage.getItem("full_name");
  const [activeTab, setActiveTab] = useState<TabKey>("global");

  // Data states
  const [perfData, setPerfData] = useState<any>(null);
  const [attData, setAttData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Filter states
  const [perfFilters, setPerfFilters] = useState({ branch: "", level: "", semester: "", year: "" });
  const [attFilters, setAttFilters] = useState({ day: "", month: "", semester: "", year: "", zone: "" });

  // Filter options from API (stored as-is from filter_options, keys are plural)
  const [perfOptions, setPerfOptions] = useState<any>({});
  const [attOptions, setAttOptions] = useState<any>({});

  const token = localStorage.getItem("token");
  const API_URL = import.meta.env.VITE_API_URL;

  // =========================================================
  // FETCH PERFORMANCE DATA
  // =========================================================
  const fetchPerformance = async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      Object.entries(perfFilters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });

      const res = await axios.get(
        `${API_URL}/dashboard/performance?${params}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setPerfData(res.data);
      // Store filter_options directly — keys are plural (branches, levels, semesters, years)
      // FilterBar will use optionsKey to look them up correctly
      setPerfOptions(res.data.filter_options || {});
    } catch (err) {
      setError("Erreur de chargement des données de performance");
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // FETCH ATTENDANCE DATA
  // =========================================================
  const fetchAttendance = async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      Object.entries(attFilters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });

      const res = await axios.get(
        `${API_URL}/dashboard/attendance?${params}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setAttData(res.data);
      // Store filter_options directly — keys are plural (days, months, semesters, years, zones)
      setAttOptions(res.data.filter_options || {});
    } catch (err) {
      setError("Erreur de chargement des données de présence");
    } finally {
      setLoading(false);
    }
  };

  // Load data when tab or filters change
  useEffect(() => {
    if (activeTab === "global") fetchPerformance();
    else fetchAttendance();
  }, [activeTab, perfFilters, attFilters]);

  // =========================================================
  // PERFORMANCE CHART CONFIGS
  // =========================================================
  const subjectsChart = perfData ? {
    labels: perfData.subjects.map((s: any) => s.content_name),
    datasets: [{
      label: "Moyenne",
      data: perfData.subjects.map((s: any) => s.avg_grade),
      backgroundColor: COLORS.primary,
      borderRadius: 6,
    }]
  } : null;

  const trendsChart = perfData ? {
    labels: perfData.trends.map((t: any) => t.year_name),
    datasets: [{
      label: "Moyenne Générale",
      data: perfData.trends.map((t: any) => t.avg_grade),
      borderColor: COLORS.secondary,
      backgroundColor: "rgba(139, 92, 246, 0.1)",
      tension: 0.4,
      fill: true,
      pointRadius: 5,
      pointBackgroundColor: COLORS.secondary,
    }]
  } : null;

  const branchesChart = perfData ? {
    labels: perfData.branches.map((b: any) => b.branch_name),
    datasets: [{
      data: perfData.branches.map((b: any) => b.success_rate),
      backgroundColor: [COLORS.primary, COLORS.warning, COLORS.success, COLORS.danger, COLORS.info],
      borderWidth: 0,
    }]
  } : null;

  const levelsChart = perfData ? {
    labels: perfData.levels.map((l: any) => l.level_name),
    datasets: [{
      label: "Moyenne",
      data: perfData.levels.map((l: any) => l.avg_grade),
      backgroundColor: COLORS.secondary,
      borderRadius: 6,
    }]
  } : null;

  // =========================================================
  // ATTENDANCE CHART CONFIGS
  // =========================================================
  const daysChart = attData ? {
    labels: attData.days.map((d: any) => d.day_name),
    datasets: [{
      label: "Absences",
      data: attData.days.map((d: any) => d.absences),
      backgroundColor: COLORS.success,
      borderRadius: 6,
    }]
  } : null;

  const zonesChart = attData ? {
    labels: attData.zones.map((z: any) => z.zone_description),
    datasets: [{
      label: "Absences",
      data: attData.zones.map((z: any) => z.absences),
      backgroundColor: COLORS.primary,
      borderRadius: 6,
    }]
  } : null;

  const monthsChart = attData ? {
    labels: attData.months.map((m: any) => m.month_name),
    datasets: [{
      label: "Absences",
      data: attData.months.map((m: any) => m.absences),
      backgroundColor: COLORS.warning,
      borderRadius: 6,
    }]
  } : null;

  const weatherChart = attData ? {
    labels: attData.weather.map((w: any) => w.condition),
    datasets: [{
      data: attData.weather.map((w: any) => w.absences),
      backgroundColor: [COLORS.info, COLORS.warning],
      borderWidth: 0,
    }]
  } : null;

  const tempChart = attData ? {
    labels: attData.temp.map((t: any) => t.temp_band),
    datasets: [{
      data: attData.temp.map((t: any) => t.absences),
      backgroundColor: [COLORS.warning, COLORS.success, COLORS.danger],
      borderWidth: 0,
    }]
  } : null;

  // Common chart options
  const barOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, grid: { color: "#f3f4f6" } },
      x: { grid: { display: false } },
    },
  };

  const lineOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, grid: { color: "#f3f4f6" } },
      x: { grid: { display: false } },
    },
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: "bottom" as const, labels: { padding: 20 } },
    },
    cutout: "65%",
  };

  return (
    <div className="flex min-h-screen bg-[#F5F4FF]">
      <Sidebar />
      <div className="flex-1">
        <Navbar />

        <div className="p-8">
          <h1 className="text-4xl font-bold text-primary mb-2">
            Bienvenue, {fullName} 👋
          </h1>
          <p className="text-lg text-gray-600 mb-6">
            Tableau de bord analytique
          </p>

          {/* Tabs */}
          <div className="flex gap-4 mb-6">
            <button
              onClick={() => setActiveTab("global")}
              className={`px-6 py-2 rounded-xl font-semibold transition ${
                activeTab === "global" ? "bg-primary text-white" : "bg-white shadow hover:bg-gray-50"
              }`}
            >
              Dashboard Global
            </button>
            <button
              onClick={() => setActiveTab("attendance")}
              className={`px-6 py-2 rounded-xl font-semibold transition ${
                activeTab === "attendance" ? "bg-primary text-white" : "bg-white shadow hover:bg-gray-50"
              }`}
            >
              Student Attendance
            </button>
          </div>

          {/* Loading */}
          {loading && (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6">{error}</div>
          )}

          {/* ==================== PERFORMANCE TAB ==================== */}
          {!loading && activeTab === "global" && perfData && (
            <div className="space-y-6">
              {/* Filters — options passed as-is (plural keys), config has optionsKey to bridge the gap */}
              <FilterBar
                filters={perfFilters}
                options={perfOptions}
                config={PERF_FILTER_CONFIG}
                onChange={(key, value) => setPerfFilters(prev => ({ ...prev, [key]: value }))}
                onClear={() => setPerfFilters({ branch: "", level: "", semester: "", year: "" })}
              />

              {/* KPI Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <KPICard title="Moyenne Générale" value={perfData.kpi.avg_grade || "0"} />
                <KPICard title="Taux de Réussite %" value={`${perfData.kpi.success_rate || "0"}%`} />
                <KPICard title="Total Évaluations" value={perfData.kpi.total_evaluations || "0"} />
              </div>

              {/* Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ChartCard title="Moyenne par Matière" className="h-80">
                  {subjectsChart && <Bar data={subjectsChart} options={barOptions} />}
                </ChartCard>
                <ChartCard title="Évolution des Moyennes" className="h-80">
                  {trendsChart && <Line data={trendsChart} options={lineOptions} />}
                </ChartCard>
                <ChartCard title="Taux de Réussite par Filière" className="h-80">
                  {branchesChart && <Doughnut data={branchesChart} options={doughnutOptions} />}
                </ChartCard>
                <ChartCard title="Moyenne par Niveau" className="h-80">
                  {levelsChart && <Bar data={levelsChart} options={barOptions} />}
                </ChartCard>
              </div>
            </div>
          )}

          {/* ==================== ATTENDANCE TAB ==================== */}
          {!loading && activeTab === "attendance" && attData && (
            <div className="space-y-6">
              {/* Filters — options passed as-is (plural keys), config has optionsKey to bridge the gap */}
              <FilterBar
                filters={attFilters}
                options={attOptions}
                config={ATT_FILTER_CONFIG}
                onChange={(key, value) => setAttFilters(prev => ({ ...prev, [key]: value }))}
                onClear={() => setAttFilters({ day: "", month: "", semester: "", year: "", zone: "" })}
              />

              {/* KPI */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <KPICard title="Total Absences" value={attData.kpi.total_absences || "0"} />
              </div>

              {/* Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <ChartCard title="Absences par Jour" className="h-80">
                  {daysChart && <Bar data={daysChart} options={barOptions} />}
                </ChartCard>
                <ChartCard title="Absences par Zone" className="h-80">
                  {zonesChart && <Bar data={zonesChart} options={barOptions} />}
                </ChartCard>
                <ChartCard title="Absences par Mois" className="h-80">
                  {monthsChart && <Bar data={monthsChart} options={barOptions} />}
                </ChartCard>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ChartCard title="Absences: Pluie vs Sans Pluie" className="h-80">
                  {weatherChart && <Doughnut data={weatherChart} options={doughnutOptions} />}
                </ChartCard>
                <ChartCard title="Absences par Température" className="h-80">
                  {tempChart && <Doughnut data={tempChart} options={doughnutOptions} />}
                </ChartCard>
              </div>

              {/* Student Grid Table */}
              <ChartCard title="Grille d'Absences par Élève" className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-3 px-2">Élève</th>
                      <th className="text-center py-3 px-2">Lun</th>
                      <th className="text-center py-3 px-2">Mar</th>
                      <th className="text-center py-3 px-2">Mer</th>
                      <th className="text-center py-3 px-2">Jeu</th>
                      <th className="text-center py-3 px-2">Ven</th>
                      <th className="text-center py-3 px-2">Sam</th>
                      <th className="text-center py-3 px-2 font-bold">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attData.grid.map((row: any, idx: number) => (
                      <tr key={idx} className="border-b hover:bg-gray-50">
                        <td className="py-2 px-2">{row.student_full_name_arab}</td>
                        <td className="text-center py-2 px-2">{row.Lundi || "-"}</td>
                        <td className="text-center py-2 px-2">{row.Mardi || "-"}</td>
                        <td className="text-center py-2 px-2">{row.Mercredi || "-"}</td>
                        <td className="text-center py-2 px-2">{row.Jeudi || "-"}</td>
                        <td className="text-center py-2 px-2">{row.Vendredi || "-"}</td>
                        <td className="text-center py-2 px-2">{row.Samedi || "-"}</td>
                        <td className="text-center py-2 px-2 font-bold">{row.RowTotal}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </ChartCard>
            </div>
          )}
        </div>
      </div>
      <ChatWidget />
    </div>
  );
}