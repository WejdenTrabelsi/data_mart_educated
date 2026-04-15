/**
 * STUDENT PERFORMANCE DASHBOARD
 * ----------------------------
 * This dashboard visualizes student performance data from a Data Warehouse
 * Uses React Hooks and Chart.js for interactive data visualization
 * 
 * Colors follow Educated platform brand guidelines:
 * - Primary: #504BED (purple)
 * - Secondary: #FF6920 (dark orange)
 * - Accent: #FF9906 (light orange)
 */

import { useState, useEffect, useMemo, useRef } from 'react';  // ✅ Added useRef
import { Chart, registerables } from 'chart.js';
import './styles/dashboard.css';

// Register all Chart.js components (required for charts to work)
Chart.register(...registerables);

// ============================================
// CONSTANTS & CONFIGURATION
// ============================================

// Educated platform brand colors
const COLORS = {
  purple: '#504BED',      // Primary brand color
  orange: '#FF6920',      // Dark orange for emphasis
  orangeLight: '#FF9906', // Light orange for accents
  white: '#FFFFFF',
  bgGray: '#F5F4FF',      // Light purple-tinted background
  text: '#1A1A2E',        // Dark text
  textMuted: '#6B6B8A',   // Secondary text
  border: '#D9D8FF',      // Border color
  success: '#00C27C'      // Green for success rates
};

// ✅ FIXED: API base URL - changed to port 3001 (matches your server.js)
const API_BASE_URL = 'http://localhost:3001';

// ============================================
// CUSTOM HOOK: Fetch Data from Database
// ============================================

/**
 * Custom hook to fetch data from our API
 * @param {string} endpoint - API endpoint to call (e.g., '/api/dimensions')
 * @param {object} params - Query parameters (filters)
 * @returns {object} { data, loading, error }
 */
function useFetch(endpoint, params = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // Build query string from params (filter out 'all' values)
        const queryParams = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
          if (value && value !== 'all') {
            queryParams.append(key, value);
          }
        });
        
        const queryString = queryParams.toString();
        const url = `${API_BASE_URL}${endpoint}${queryString ? `?${queryString}` : ''}`;
        
        console.log(`Fetching: ${url}`); // For debugging
        
        const response = await fetch(url);
        
        if (!response.ok) throw new Error(`Failed to fetch data: ${response.status}`);
        
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err.message);
        console.error('Fetch error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [endpoint, JSON.stringify(params)]);

  return { data, loading, error };
}

// ============================================
// MAIN APP COMPONENT
// ============================================

export default function App() {
  // State for filters
  const [selectedYear, setSelectedYear] = useState('all');
  const [selectedLevel, setSelectedLevel] = useState('all');
  const [selectedBranch, setSelectedBranch] = useState('all');

  // ✅ FIXED: Fetch dimension data for filters (using correct endpoints)
  const { data: dimensions, loading: dimsLoading } = useFetch('/api/dimensions');
  
  // Fetch all statistics based on current filters
  const filters = { year: selectedYear, level: selectedLevel, branch: selectedBranch };
  const { data: stats, loading: statsLoading } = useFetch('/api/stats', filters);
  const { data: subjectData } = useFetch('/api/by-subject', filters);
  const { data: levelData } = useFetch('/api/by-level', { year: selectedYear, branch: selectedBranch });
  const { data: branchData } = useFetch('/api/by-branch', { year: selectedYear, level: selectedLevel });
  const { data: trendData } = useFetch('/api/trend', { level: selectedLevel, branch: selectedBranch });

  // Calculate overall metrics
  const metrics = useMemo(() => ({
    totalStudents: stats?.totalStudents?.toLocaleString() || '0',
    avgGrade: stats?.avgGrade ? stats.avgGrade.toFixed(2) : '0',
    passRate: stats?.avgSuccessRate ? stats.avgSuccessRate.toFixed(1) : '0',
    uniqueSubjects: stats?.uniqueSubjects || 0
  }), [stats]);

  // Prepare chart data for subjects (horizontal bar chart)
  const subjectChartData = useMemo(() => {
    if (!subjectData || subjectData.length === 0) return null;
    return {
      labels: subjectData.map(item => item.subject),
      datasets: [{
        label: 'Pass Rate (%)',
        data: subjectData.map(item => parseFloat(item.passRate.toFixed(1))),
        backgroundColor: subjectData.map(item => 
          item.passRate >= 70 ? COLORS.purple : 
          item.passRate >= 50 ? COLORS.orangeLight : 
          COLORS.orange
        ),
        borderRadius: 6,
        barThickness: 25
      }]
    };
  }, [subjectData]);

  // Prepare chart data for levels (vertical bar chart)
  const levelChartData = useMemo(() => {
    if (!levelData || levelData.length === 0) return null;
    return {
      labels: levelData.map(item => item.level),
      datasets: [{
        label: 'Pass Rate (%)',
        data: levelData.map(item => parseFloat(item.passRate.toFixed(1))),
        backgroundColor: COLORS.purple,
        borderRadius: 8
      }]
    };
  }, [levelData]);

  // Prepare chart data for branches (doughnut chart)
  const branchChartData = useMemo(() => {
    if (!branchData || branchData.length === 0) return null;
    return {
      labels: branchData.map(item => item.branch),
      datasets: [{
        data: branchData.map(item => parseFloat(item.passRate.toFixed(1))),
        backgroundColor: [COLORS.purple, COLORS.orange, COLORS.orangeLight, '#8F8CF5', '#FFB347'],
        borderWidth: 3,
        borderColor: COLORS.white
      }]
    };
  }, [branchData]);

  // Prepare chart data for trend (line chart)
  const trendChartData = useMemo(() => {
    if (!trendData || trendData.length === 0) return null;
    return {
      labels: trendData.map(item => item.year),
      datasets: [{
        label: 'Average Grade (/20)',
        data: trendData.map(item => parseFloat(item.avgGrade.toFixed(2))),
        borderColor: COLORS.purple,
        backgroundColor: 'rgba(80,75,237,0.1)',
        borderWidth: 3,
        pointBackgroundColor: COLORS.orange,
        pointBorderColor: COLORS.white,
        pointRadius: 6,
        pointHoverRadius: 8,
        fill: true,
        tension: 0.3
      }]
    };
  }, [trendData]);

  // Chart configuration options (shared)
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { font: { size: 12 }, color: COLORS.text } },
      tooltip: { backgroundColor: COLORS.white, titleColor: COLORS.text, bodyColor: COLORS.text }
    }
  };

  // Horizontal bar chart specific options
  const horizontalBarOptions = {
    ...chartOptions,
    indexAxis: 'y',
    plugins: { ...chartOptions.plugins, legend: { display: false } },
    scales: {
      x: { title: { display: true, text: 'Pass Rate (%)' }, min: 0, max: 100 },
      y: { grid: { display: false } }
    }
  };

  // Line chart specific options
  const lineOptions = {
    ...chartOptions,
    plugins: { ...chartOptions.plugins, legend: { position: 'top' } },
    scales: {
      y: { title: { display: true, text: 'Grade (/20)' }, min: 0, max: 20 }
    }
  };

  // Reset all filters to default
  const resetFilters = () => {
    setSelectedYear('all');
    setSelectedLevel('all');
    setSelectedBranch('all');
  };

  if (dimsLoading) {
    return <div className="loading">Loading dashboard...</div>;
  }

  return (
    <div className="dashboard">
      {/* Header Section */}
      <header className="dashboard-header">
        <div className="brand-accent"></div>
        <div>
          <h1>Student Performance Dashboard</h1>
          <p>Academic analytics · Educated platform</p>
        </div>
      </header>

      {/* Filters Section */}
      <div className="filters-container">
        <FilterSelect 
          label="School Year" 
          value={selectedYear} 
          onChange={setSelectedYear}
          options={dimensions?.years || []}
        />
        <FilterSelect 
          label="Level" 
          value={selectedLevel} 
          onChange={setSelectedLevel}
          options={dimensions?.levels || []}
        />
        <FilterSelect 
          label="Branch" 
          value={selectedBranch} 
          onChange={setSelectedBranch}
          options={dimensions?.branches || []}
        />
        <button className="reset-btn" onClick={resetFilters}>
          Reset Filters
        </button>
      </div>

      {/* KPI Metrics Cards */}
      <div className="metrics-grid">
        <MetricCard 
          label="Total Students" 
          value={metrics.totalStudents} 
          subtext="assessments recorded"
          color={COLORS.purple}
        />
        <MetricCard 
          label="Average Grade" 
          value={`${metrics.avgGrade}/20`} 
          subtext="weighted average"
          color={COLORS.orange}
        />
        <MetricCard 
          label="Pass Rate" 
          value={`${metrics.passRate}%`} 
          subtext="grade ≥ 10/20"
          color={COLORS.success}
        />
        <MetricCard 
          label="Subjects" 
          value={metrics.uniqueSubjects} 
          subtext="in current view"
          color={COLORS.orangeLight}
        />
      </div>

      {/* Charts Section */}
      <div className="charts-grid">
        {/* Chart 1: Pass Rate by Subject (Horizontal Bar) */}
        <div className="chart-card wide">
          <h3>Pass Rate by Subject</h3>
          <p className="chart-subtitle">
            <span className="legend purple">≥70%</span>
            <span className="legend orange-light">50-69%</span>
            <span className="legend orange">&lt;50%</span>
          </p>
          <div className="chart-container">
            {subjectChartData && (
              <ChartComponent 
                type="bar" 
                data={subjectChartData} 
                options={horizontalBarOptions}
              />
            )}
          </div>
        </div>

        {/* Chart 2: Pass Rate by Level */}
        <div className="chart-card">
          <h3>Pass Rate by Level</h3>
          <div className="chart-container">
            {levelChartData && (
              <ChartComponent 
                type="bar" 
                data={levelChartData} 
                options={chartOptions}
              />
            )}
          </div>
        </div>

        {/* Chart 3: Pass Rate by Branch (Doughnut) */}
        <div className="chart-card">
          <h3>Pass Rate by Branch</h3>
          <div className="chart-container">
            {branchChartData && (
              <ChartComponent 
                type="doughnut" 
                data={branchChartData} 
                options={{ ...chartOptions, cutout: '60%' }}
              />
            )}
          </div>
        </div>

        {/* Chart 4: Grade Trend Over Years (Line) */}
        <div className="chart-card wide">
          <h3>Grade Trend Over Years</h3>
          <div className="chart-container">
            {trendChartData && (
              <ChartComponent 
                type="line" 
                data={trendChartData} 
                options={lineOptions}
              />
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="dashboard-footer">
        Data source: StudentPerformanceDW · Fact_StudentPerformance
      </footer>
    </div>
  );
}

// ============================================
// CHART COMPONENT (Handles Chart.js lifecycle)
// ============================================

function ChartComponent({ type, data, options }) {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    if (!chartRef.current) return;
    
    // Destroy existing chart instance to prevent memory leaks
    if (chartInstance.current) {
      chartInstance.current.destroy();
    }
    
    // Create new chart
    chartInstance.current = new Chart(chartRef.current, {
      type: type,
      data: data,
      options: options
    });
    
    // Cleanup on unmount
    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
    };
  }, [type, data, options]);

  return <canvas ref={chartRef}></canvas>;
}

// ============================================
// FILTER SELECT COMPONENT
// ============================================

function FilterSelect({ label, value, onChange, options }) {
  return (
    <div className="filter-group">
      <label>{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="all">All {label}s</option>
        {options.map(opt => (
          <option key={opt.id} value={opt.id}>{opt.name}</option>
        ))}
      </select>
    </div>
  );
}

// ============================================
// METRIC CARD COMPONENT
// ============================================

function MetricCard({ label, value, subtext, color }) {
  return (
    <div className="metric-card" style={{ borderTopColor: color }}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
      {subtext && <span className="metric-subtext">{subtext}</span>}
    </div>
  );
}