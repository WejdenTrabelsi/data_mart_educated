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
import logo from "../assets/logo.png"; // ← Logo import

// Register Chart.js components once
ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, ArcElement, Title, Tooltip, Legend);

type TabKey = "global" | "attendance";

// ── Color palette ──
const COLORS = {
  primary: "#6366f1", secondary: "#8b5cf6", success: "#22c55e",
  warning: "#f59e0b", danger: "#ef4444", info: "#3b82f6",
  purple: "#a855f7", pink: "#ec4899", teal: "#14b8a6", orange: "#f97316",
};

// ── Filter configurations ──
const PERF_FILTER_CONFIG = [
  { key: "branch", label: "Filière", optionsKey: "branches" },
  { key: "level", label: "Niveau", optionsKey: "levels" },
  { key: "semester", label: "Semestre", optionsKey: "semesters" },
  { key: "year", label: "Année", optionsKey: "years" },
];

const ATT_FILTER_CONFIG = [
  { key: "day", label: "Jour", optionsKey: "days" },
  { key: "month", label: "Mois", optionsKey: "months" },
  { key: "semester", label: "Semestre", optionsKey: "semesters" },
  { key: "year", label: "Année", optionsKey: "years" },
  { key: "zone", label: "Zone", optionsKey: "zones" },
];

// ═══════════════════════════════════════════════════════════════
// CHART HELPERS — keeps the component DRY
// ═══════════════════════════════════════════════════════════════

/** Build a bar chart dataset */
const barChart = (labels: string[], data: number[], label: string, color: string) => ({
  labels,
  datasets: [{ label, data, backgroundColor: color, borderRadius: 6 }],
});

/** Build a line chart dataset */
const lineChart = (labels: string[], data: number[], label: string, color: string) => ({
  labels,
  datasets: [{
    label, data, borderColor: color,
    backgroundColor: `${color}1A`, // 10 % opacity
    tension: 0.4, fill: true, pointRadius: 5, pointBackgroundColor: color,
  }],
});

/** Build a doughnut chart dataset */
const doughnutChart = (labels: string[], data: number[], colors: string[]) => ({
  labels,
  datasets: [{ data, backgroundColor: colors, borderWidth: 0 }],
});

// ── Common Chart.js options ──
// Added bottom padding + maxRotation so x-axis labels never overflow the white card
const commonOpts = {
  responsive: true,
  maintainAspectRatio: false,
  layout: { padding: { bottom: 20 } },
};

const barOpts = {
  ...commonOpts,
  plugins: { legend: { display: false } },
  scales: {
    y: { beginAtZero: true, grid: { color: "#f3f4f6" } },
    x: { grid: { display: false }, ticks: { maxRotation: 45, minRotation: 0 } },
  },
};

const lineOpts = {
  ...commonOpts,
  plugins: { legend: { display: false } },
  scales: {
    y: { beginAtZero: true, grid: { color: "#f3f4f6" } },
    x: { grid: { display: false } },
  },
};

const doughnutOpts = {
  ...commonOpts,
  plugins: { legend: { position: "bottom" as const, labels: { padding: 20 } } },
  cutout: "65%",
};

// ═══════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════

export default function Dashboard() {
  const fullName = localStorage.getItem("full_name");
  const token = localStorage.getItem("token");
  const API_URL = import.meta.env.VITE_API_URL;

  const [activeTab, setActiveTab] = useState<TabKey>("global");

  // Data & UI states
  const [perfData, setPerfData] = useState<any>(null);
  const [attData, setAttData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Filters
  const [perfFilters, setPerfFilters] = useState({ branch: "", level: "", semester: "", year: "" });
  const [attFilters, setAttFilters] = useState({ day: "", month: "", semester: "", year: "", zone: "" });

  // Dropdown options returned by backend
  const [perfOptions, setPerfOptions] = useState<any>({});
  const [attOptions, setAttOptions] = useState<any>({});

  // ── Generic fetcher for both endpoints ──
  useEffect(() => {
    const fetchData = async (
      endpoint: string,
      filters: Record<string, string>,
      setData: (d: any) => void,
      setOpts: (o: any) => void,
    ) => {
      setLoading(true);
      setError("");
      try {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([k, v]) => v && params.append(k, v));
        const res = await axios.get(`${API_URL}${endpoint}?${params}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setData(res.data);
        setOpts(res.data.filter_options || {});
      } catch {
        setError("Erreur de chargement des données");
      } finally {
        setLoading(false);
      }
    };

    if (activeTab === "global") {
      fetchData("/dashboard/performance", perfFilters, setPerfData, setPerfOptions);
    } else {
      fetchData("/dashboard/attendance", attFilters, setAttData, setAttOptions);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, perfFilters, attFilters]);

  // ── Performance charts (memo-like helpers) ──
  const subjectsChart = perfData
    ? barChart(perfData.subjects.map((s: any) => s.content_name), perfData.subjects.map((s: any) => s.avg_grade), "Moyenne", COLORS.primary)
    : null;

  const trendsChart = perfData
    ? lineChart(perfData.trends.map((t: any) => t.year_name), perfData.trends.map((t: any) => t.avg_grade), "Moyenne Générale", COLORS.secondary)
    : null;

  // ↓ Changed to bar chart as requested — pie/doughnut was misleading for comparing rates
  const branchesChart = perfData
    ? barChart(perfData.branches.map((b: any) => b.branch_name), perfData.branches.map((b: any) => b.success_rate), "Taux %", COLORS.warning)
    : null;

  const levelsChart = perfData
    ? barChart(perfData.levels.map((l: any) => l.level_name), perfData.levels.map((l: any) => l.avg_grade), "Moyenne", COLORS.secondary)
    : null;

  // ── Attendance charts ──
  const daysChart = attData
    ? barChart(attData.days.map((d: any) => d.day_name), attData.days.map((d: any) => d.absences), "Absences", COLORS.success)
    : null;

  const zonesChart = attData
    ? barChart(attData.zones.map((z: any) => z.zone_description), attData.zones.map((z: any) => z.absences), "Absences", COLORS.primary)
    : null;

  const monthsChart = attData
    ? barChart(attData.months.map((m: any) => m.month_name), attData.months.map((m: any) => m.absences), "Absences", COLORS.warning)
    : null;

  const weatherChart = attData
    ? doughnutChart(attData.weather.map((w: any) => w.condition), attData.weather.map((w: any) => w.absences), [COLORS.info, COLORS.warning])
    : null;

  const tempChart = attData
    ? doughnutChart(attData.temp.map((t: any) => t.temp_band), attData.temp.map((t: any) => t.absences), [COLORS.warning, COLORS.success, COLORS.danger])
    : null;

  return (
    <div className="flex min-h-screen bg-[#F5F4FF]">
      <Sidebar />

      <div className="flex-1">
        <Navbar />

        <div className="p-8">
          {/* ═══════ HEADER: Logo + Welcome ═══════ */}
          <div className="flex items-center gap-6 mb-6">
            <img src={logo} alt="Logo" className="h-34 w-auto object-contain" />
            <div>
              <h1 className="text-4xl font-bold text-primary">Bienvenue, {fullName} 👋</h1>
              <p className="text-lg text-gray-600">Tableau de bord analytique</p>
            </div>
          </div>

          {/* ═══════ TABS ═══════ */}
          <div className="flex gap-4 mb-6">
            {[
              { key: "global", label: "Dashboard Global" },
              { key: "attendance", label: "Student Attendance" },
            ].map((t) => (
              <button
                key={t.key}
                onClick={() => setActiveTab(t.key as TabKey)}
                className={`px-6 py-2 rounded-xl font-semibold transition ${
                  activeTab === t.key ? "bg-primary text-white" : "bg-white shadow hover:bg-gray-50"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* ═══════ STATES ═══════ */}
          {loading && (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
            </div>
          )}

          {error && <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6">{error}</div>}

          {/* ═══════════════════════════════════════════════════════════════
              PERFORMANCE TAB
          ═══════════════════════════════════════════════════════════════ */}
          {!loading && activeTab === "global" && perfData && (
            <div className="space-y-6">
              {/* Filters */}
              <FilterBar
                filters={perfFilters}
                options={perfOptions}
                config={PERF_FILTER_CONFIG}
                onChange={(key, value) => setPerfFilters((p) => ({ ...p, [key]: value }))}
                onClear={() => setPerfFilters({ branch: "", level: "", semester: "", year: "" })}
              />

              {/* KPIs */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <KPICard title="Moyenne Générale" value={perfData.kpi.avg_grade || "0"} />
                <KPICard title="Taux de Réussite %" value={`${perfData.kpi.success_rate || "0"}%`} />
                <KPICard title="Total Évaluations" value={perfData.kpi.total_evaluations || "0"} />
              </div>

              {/* Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ChartCard title="Moyenne par Matière" className="h-80">
                  {subjectsChart && <Bar data={subjectsChart} options={barOpts} />}
                </ChartCard>

                <ChartCard title="Évolution des Moyennes" className="h-80">
                  {trendsChart && <Line data={trendsChart} options={lineOpts} />}
                </ChartCard>

                <ChartCard title="Taux de Réussite par Filière" className="h-80">
                  {branchesChart && <Bar data={branchesChart} options={barOpts} />}
                </ChartCard>

                <ChartCard title="Moyenne par Niveau" className="h-80">
                  {levelsChart && <Bar data={levelsChart} options={barOpts} />}
                </ChartCard>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════
              ATTENDANCE TAB
          ═══════════════════════════════════════════════════════════════ */}
          {!loading && activeTab === "attendance" && attData && (
            <div className="space-y-6">
              {/* Filters */}
              <FilterBar
                filters={attFilters}
                options={attOptions}
                config={ATT_FILTER_CONFIG}
                onChange={(key, value) => setAttFilters((p) => ({ ...p, [key]: value }))}
                onClear={() => setAttFilters({ day: "", month: "", semester: "", year: "", zone: "" })}
              />

              {/* KPI */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <KPICard title="Total Absences" value={attData.kpi.total_absences || "0"} />
              </div>

              {/* Charts row 1 */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <ChartCard title="Absences par Jour" className="h-80">
                  {daysChart && <Bar data={daysChart} options={barOpts} />}
                </ChartCard>
                <ChartCard title="Absences par Zone" className="h-80">
                  {zonesChart && <Bar data={zonesChart} options={barOpts} />}
                </ChartCard>
                <ChartCard title="Absences par Mois" className="h-80">
                  {monthsChart && <Bar data={monthsChart} options={barOpts} />}
                </ChartCard>
              </div>

              {/* Charts row 2 */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ChartCard title="Absences: Pluie vs Sans Pluie" className="h-80">
                  {weatherChart && <Doughnut data={weatherChart} options={doughnutOpts} />}
                </ChartCard>
                <ChartCard title="Absences par Température" className="h-80">
                  {tempChart && <Doughnut data={tempChart} options={doughnutOpts} />}
                </ChartCard>
              </div>

              {/* Student grid */}
              <ChartCard title="Grille d'Absences par Élève" className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      {["Élève", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Total"].map((h) => (
                        <th key={h} className={`py-3 px-2 ${h === "Total" ? "font-bold" : h === "Élève" ? "text-left" : "text-center"}`}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {attData.grid.map((row: any, idx: number) => (
                      <tr key={idx} className="border-b hover:bg-gray-50">
                        <td className="py-2 px-2">{row.student_full_name_arab}</td>
                        {["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"].map((d) => (
                          <td key={d} className="text-center py-2 px-2">{row[d] || "-"}</td>
                        ))}
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

      {/* Floating chat */}
      <ChatWidget />
    </div>
  );
}