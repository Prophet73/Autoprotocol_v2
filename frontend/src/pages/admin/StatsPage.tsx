import { useEffect, useState, useMemo, useRef } from 'react';
import { getApiErrorMessage } from '../../utils/errorMessage';
import { useConfirm } from '../../hooks/useConfirm';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarController,
  LineController,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  type ChartData,
  type ChartOptions,
} from 'chart.js';
import { Chart } from 'react-chartjs-2';
import {
  comprehensiveStatsApi,
  type FullDashboardResponse,
  type StatsFilters,
  type AdminDomainInfo,
  type DomainStatsResponse,
  type CostStatsResponse,
  type TimelinePoint,
} from '../../api/adminApi';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarController,
  LineController,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler,
);

type TabId = 'overview' | 'domains' | 'users' | 'costs';

interface Tab {
  id: TabId;
  name: string;
  icon: React.ReactNode;
}

const tabs: Tab[] = [
  {
    id: 'overview',
    name: 'Обзор',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    id: 'domains',
    name: 'Домены',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    ),
  },
  {
    id: 'users',
    name: 'Пользователи',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
      </svg>
    ),
  },
  {
    id: 'costs',
    name: 'Затраты AI',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
];

// KPI Card component
interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color: string;
  trend?: { value: number; positive: boolean };
}

function KPICard({ title, value, subtitle, icon, color, trend }: KPICardProps) {
  return (
    <div className="bg-white rounded-lg p-5 shadow-sm border border-slate-200">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-slate-500 text-sm">{title}</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">{value}</p>
          {subtitle && <p className="text-slate-400 text-xs mt-1">{subtitle}</p>}
          {trend && (
            <div className={`flex items-center mt-2 text-xs ${trend.positive ? 'text-green-600' : 'text-red-600'}`}>
              {trend.positive ? (
                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
              {trend.value}%
            </div>
          )}
        </div>
        <div className={`w-12 h-12 ${color} rounded-lg flex items-center justify-center flex-shrink-0`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

// Progress bar component
function ProgressBar({ value, max, label, color }: { value: number; max: number; label: string; color: string }) {
  const percentage = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="mb-3">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-slate-600">{label}</span>
        <span className="text-slate-800">{value}</span>
      </div>
      <div className="w-full bg-slate-200 rounded-full h-2">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${Math.min(percentage, 100)}%` }} />
      </div>
    </div>
  );
}

// Dual-axis timeline chart: bars for jobs, line for unique users
function TimelineChart({ points }: { points: TimelinePoint[] }) {
  const chartRef = useRef<ChartJS<'bar'>>(null);

  const data: ChartData<'bar' | 'line', number[], string> = useMemo(() => {
    const labels = points.map(p =>
      new Date(p.date).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })
    );
    return {
      labels,
      datasets: [
        {
          type: 'bar' as const,
          label: 'Обработок',
          data: points.map(p => p.jobs),
          backgroundColor: 'rgba(216, 30, 5, 0.75)',
          hoverBackgroundColor: 'rgba(216, 30, 5, 1)',
          borderRadius: 3,
          borderSkipped: false,
          order: 2,
        },
        {
          type: 'line' as const,
          label: 'Уникальных пользователей',
          data: points.map(p => p.unique_users),
          borderColor: '#0D2C54',
          backgroundColor: 'rgba(13, 44, 84, 0.1)',
          borderWidth: 2,
          pointRadius: 3,
          pointHoverRadius: 5,
          pointBackgroundColor: '#0D2C54',
          fill: true,
          tension: 0.3,
          order: 1,
        },
      ],
    };
  }, [points]);

  const options: ChartOptions<'bar' | 'line'> = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          usePointStyle: true,
          pointStyle: 'rectRounded',
          padding: 16,
          font: { size: 12, family: 'Manrope, sans-serif' },
        },
      },
      tooltip: {
        backgroundColor: 'rgba(255,255,255,0.95)',
        titleColor: '#1e293b',
        bodyColor: '#475569',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        padding: 10,
        titleFont: { weight: 'bold' as const },
        callbacks: {
          title: (items) => {
            if (!items.length) return '';
            const idx = items[0].dataIndex;
            const p = points[idx];
            return new Date(p.date).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
          },
          afterBody: (items) => {
            if (!items.length) return '';
            const idx = items[0].dataIndex;
            const p = points[idx];
            return `Успешных: ${p.completed} / Ошибок: ${p.failed}`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: {
          font: { size: 11 },
          maxRotation: 45,
          autoSkip: true,
          maxTicksLimit: 15,
        },
      },
      y: {
        type: 'linear' as const,
        position: 'left' as const,
        beginAtZero: true,
        ticks: {
          stepSize: 1,
          font: { size: 11 },
        },
        grid: { color: 'rgba(0,0,0,0.06)' },
      },
    },
  }), [points]);

  return (
    <div style={{ height: 300 }}>
      <Chart ref={chartRef} type="bar" data={data as ChartData<'bar', number[], string>} options={options as ChartOptions<'bar'>} />
    </div>
  );
}

export default function StatsPage() {
  const { alert, ConfirmDialog } = useConfirm();
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Data states
  const [dashboard, setDashboard] = useState<FullDashboardResponse | null>(null);
  const [domains, setDomains] = useState<AdminDomainInfo[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<string>('');
  const [domainStats, setDomainStats] = useState<DomainStatsResponse | null>(null);
  const [costStats, setCostStats] = useState<CostStatsResponse | null>(null);

  // Filters — default to current month
  const [filters, setFilters] = useState<StatsFilters>({});
  const [dateFrom, setDateFrom] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
  });
  const [dateTo, setDateTo] = useState('');

  // Load initial data
  useEffect(() => {
    loadDashboard();
    loadDomains();
  }, []);

  // Load domain stats when selected
  useEffect(() => {
    if (selectedDomain && activeTab === 'domains') {
      loadDomainStats(selectedDomain);
    }
  }, [selectedDomain, activeTab]);

  // Load cost stats when tab is active
  useEffect(() => {
    if (activeTab === 'costs') {
      loadCostStats();
    }
  }, [activeTab]);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      const appliedFilters: StatsFilters = { ...filters };
      if (dateFrom) appliedFilters.date_from = dateFrom;
      if (dateTo) appliedFilters.date_to = dateTo;

      const data = await comprehensiveStatsApi.getDashboard(appliedFilters);
      setDashboard(data);
      setError('');
    } catch (err) {
      setError(getApiErrorMessage(err, 'Ошибка загрузки статистики'));
    } finally {
      setLoading(false);
    }
  };

  const loadDomains = async () => {
    try {
      const data = await comprehensiveStatsApi.getDomains();
      setDomains(data.domains);
      if (data.domains.length > 0 && !selectedDomain) {
        setSelectedDomain(data.domains[0].id);
      }
    } catch (err) {
      console.error('Failed to load domains:', err);
    }
  };

  const loadDomainStats = async (domainId: string) => {
    try {
      const appliedFilters: StatsFilters = { ...filters };
      if (dateFrom) appliedFilters.date_from = dateFrom;
      if (dateTo) appliedFilters.date_to = dateTo;

      const data = await comprehensiveStatsApi.getDomainStats(domainId, appliedFilters);
      setDomainStats(data);
    } catch (err) {
      console.error('Failed to load domain stats:', err);
    }
  };

  const loadCostStats = async () => {
    try {
      const appliedFilters: StatsFilters = { ...filters };
      if (dateFrom) appliedFilters.date_from = dateFrom;
      if (dateTo) appliedFilters.date_to = dateTo;

      const data = await comprehensiveStatsApi.getCostsStats(appliedFilters);
      setCostStats(data);
    } catch (err) {
      console.error('Failed to load cost stats:', err);
    }
  };

  const applyFilters = () => {
    loadDashboard();
    if (selectedDomain && activeTab === 'domains') {
      loadDomainStats(selectedDomain);
    }
    if (activeTab === 'costs') {
      loadCostStats();
    }
  };

  const clearFilters = () => {
    setDateFrom('');
    setDateTo('');
    setFilters({});
    loadDashboard();
  };

  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    try {
      setExporting(true);
      const appliedFilters: StatsFilters = { ...filters };
      if (dateFrom) appliedFilters.date_from = dateFrom;
      if (dateTo) appliedFilters.date_to = dateTo;
      await comprehensiveStatsApi.exportExcel(appliedFilters);
    } catch (err) {
      await alert('Ошибка экспорта: ' + getApiErrorMessage(err, 'неизвестная ошибка'));
    } finally {
      setExporting(false);
    }
  };

  // Timeline chart data — all points from the period
  const timelinePoints = useMemo(() => {
    if (!dashboard?.timeline?.points) return [];
    return dashboard.timeline.points;
  }, [dashboard]);

  if (loading && !dashboard) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error && !dashboard) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">{error}</p>
        <button onClick={loadDashboard} className="mt-2 text-sm text-red-500 hover:text-red-700 underline">
          Попробовать снова
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Статистика</h1>
          <p className="text-slate-500 mt-1">Аналитика и отчёты</p>
        </div>
        <div className="flex gap-2 self-start">
          <button
            onClick={handleExport}
            disabled={exporting}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white rounded-lg transition flex items-center border border-green-700"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            {exporting ? 'Экспорт...' : 'Excel'}
          </button>
          <button
            onClick={loadDashboard}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition flex items-center border border-slate-200"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Обновить
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg p-4 shadow-sm border border-slate-200">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-sm text-slate-500 mb-1">Период с</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-severin-red focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-500 mb-1">по</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-severin-red focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-500 mb-1">Домен</label>
            <select
              value={filters.domain || ''}
              onChange={(e) => setFilters({ ...filters, domain: e.target.value || undefined })}
              className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-severin-red focus:border-transparent"
            >
              <option value="">Все домены</option>
              {domains.map(d => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>
          <button
            onClick={applyFilters}
            className="px-4 py-2 bg-severin-red hover:bg-severin-red-dark text-white rounded-lg text-sm transition"
          >
            Применить
          </button>
          <button
            onClick={clearFilters}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm transition border border-slate-200"
          >
            Сбросить
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-severin-red text-severin-red'
                  : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
              }`}
            >
              {tab.icon}
              <span className="ml-2">{tab.name}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && dashboard && (
        <OverviewTab dashboard={dashboard} timelinePoints={timelinePoints} dateFrom={dateFrom} dateTo={dateTo} />
      )}

      {activeTab === 'domains' && (
        <DomainsTab
          domains={domains}
          selectedDomain={selectedDomain}
          setSelectedDomain={setSelectedDomain}
          domainStats={domainStats}
          dashboard={dashboard}
        />
      )}

      {activeTab === 'users' && dashboard && (
        <UsersTab dashboard={dashboard} />
      )}

      {activeTab === 'costs' && (
        <CostsTab costStats={costStats} dashboard={dashboard} />
      )}

      {/* Footer */}
      {dashboard && (
        <div className="text-center text-slate-500 text-sm">
          Данные обновлены: {new Date(dashboard.generated_at).toLocaleString('ru-RU')}
        </div>
      )}
      {ConfirmDialog}
    </div>
  );
}

// Overview Tab
function formatPeriodLabel(dateFrom: string, dateTo: string): string {
  const fmt = (d: string) => {
    if (!d) return null;
    const [y, m, day] = d.split('-');
    return `${day}.${m}.${y}`;
  };
  const from = fmt(dateFrom);
  const to = fmt(dateTo);
  if (from && to) return `${from} — ${to}`;
  if (from) return `с ${from}`;
  return 'Весь период';
}

function OverviewTab({ dashboard, timelinePoints, dateFrom, dateTo }: {
  dashboard: FullDashboardResponse;
  timelinePoints: TimelinePoint[];
  dateFrom: string;
  dateTo: string;
}) {
  const { overview, domains, artifacts, errors } = dashboard;
  const periodLabel = formatPeriodLabel(dateFrom, dateTo);

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div>
        <p className="text-xs text-slate-400 mb-2 uppercase tracking-wider font-medium">{periodLabel}</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Всего обработок"
          value={overview.total_jobs}
          subtitle={`Успешных: ${overview.completed_jobs}`}
          color="bg-blue-600"
          icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>}
        />
        <KPICard
          title="Успешность"
          value={`${overview.success_rate.toFixed(1)}%`}
          subtitle={`Ошибок: ${overview.failed_jobs}`}
          color="bg-green-600"
          icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <KPICard
          title="Часы медиа"
          value={`${overview.total_audio_hours.toFixed(1)}ч`}
          subtitle={`Обработка: ${overview.total_processing_hours.toFixed(1)}ч`}
          color="bg-purple-600"
          icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <KPICard
          title="Затраты AI"
          value={`$${overview.total_cost_usd.toFixed(2)}`}
          subtitle={`Среднее: $${overview.avg_cost_per_job.toFixed(4)}/задача`}
          color="bg-yellow-600"
          icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
      </div>
      </div>

      {/* Timeline chart — full width */}
      <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Обработки за период</h3>
        {timelinePoints.length > 0 ? (
          <TimelineChart points={timelinePoints} />
        ) : (
          <p className="text-slate-400 text-center py-8">Нет данных за выбранный период</p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Domains breakdown */}
        <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">По доменам</h3>
          {domains.domains.length > 0 ? (
            <div className="space-y-3">
              {domains.domains.map(d => (
                <div key={d.domain} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <div>
                    <p className="text-slate-800 font-medium">{d.display_name}</p>
                    <p className="text-slate-500 text-sm">{d.total_jobs} обработок</p>
                  </div>
                  <div className="text-right">
                    <p className={`font-medium ${d.success_rate >= 90 ? 'text-green-600' : d.success_rate >= 70 ? 'text-yellow-600' : 'text-red-600'}`}>
                      {d.success_rate.toFixed(1)}%
                    </p>
                    <p className="text-slate-500 text-sm">${d.total_cost_usd.toFixed(2)}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-400 text-center py-8">Нет данных</p>
          )}
        </div>

        {/* Artifacts */}
        <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Артефакты</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center p-4 bg-slate-50 rounded-lg border border-slate-100">
              <p className="text-2xl font-bold text-slate-800">{artifacts.transcripts_generated}</p>
              <p className="text-slate-500 text-sm">Транскриптов</p>
              <p className="text-severin-red text-xs">{artifacts.transcript_rate.toFixed(1)}%</p>
            </div>
            <div className="text-center p-4 bg-slate-50 rounded-lg border border-slate-100">
              <p className="text-2xl font-bold text-slate-800">{artifacts.tasks_generated}</p>
              <p className="text-slate-500 text-sm">Задач</p>
              <p className="text-severin-red text-xs">{artifacts.tasks_rate.toFixed(1)}%</p>
            </div>
            <div className="text-center p-4 bg-slate-50 rounded-lg border border-slate-100">
              <p className="text-2xl font-bold text-slate-800">{artifacts.reports_generated}</p>
              <p className="text-slate-500 text-sm">Отчётов</p>
              <p className="text-severin-red text-xs">{artifacts.report_rate.toFixed(1)}%</p>
            </div>
            <div className="text-center p-4 bg-slate-50 rounded-lg border border-slate-100">
              <p className="text-2xl font-bold text-slate-800">{artifacts.analysis_generated}</p>
              <p className="text-slate-500 text-sm">Анализов</p>
              <p className="text-severin-red text-xs">{artifacts.analysis_rate.toFixed(1)}%</p>
            </div>
          </div>
        </div>

        {/* Errors */}
        <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Ошибки</h3>
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-3xl font-bold text-red-500">{errors.total_errors}</p>
              <p className="text-slate-500 text-sm">Всего ошибок ({errors.error_rate.toFixed(1)}%)</p>
            </div>
          </div>
          {Object.keys(errors.by_stage).length > 0 && (
            <div>
              <p className="text-sm text-slate-500 mb-2">По этапам:</p>
              {Object.entries(errors.by_stage).map(([stage, count]) => (
                <ProgressBar key={stage} label={stage} value={count as number} max={errors.total_errors} color="bg-red-500" />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Domains Tab
function DomainsTab({
  domains,
  selectedDomain,
  setSelectedDomain,
  domainStats,
  dashboard: _dashboard,
}: {
  domains: AdminDomainInfo[];
  selectedDomain: string;
  setSelectedDomain: (id: string) => void;
  domainStats: DomainStatsResponse | null;
  dashboard: FullDashboardResponse | null;
}) {
  return (
    <div className="space-y-6">
      {/* Domain selector */}
      <div className="flex flex-wrap gap-2">
        {domains.map(d => (
          <button
            key={d.id}
            onClick={() => setSelectedDomain(d.id)}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              selectedDomain === d.id
                ? 'bg-severin-red text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200 border border-slate-200'
            }`}
          >
            {d.name}
          </button>
        ))}
      </div>

      {domainStats ? (
        <>
          {/* Domain KPIs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <KPICard
              title="Обработок"
              value={domainStats.domain.total_jobs}
              subtitle={`Успешных: ${domainStats.domain.completed_jobs}`}
              color="bg-blue-600"
              icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>}
            />
            <KPICard
              title="Успешность"
              value={`${domainStats.domain.success_rate.toFixed(1)}%`}
              color="bg-green-600"
              icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
            />
            <KPICard
              title="Часы медиа"
              value={`${domainStats.domain.total_audio_hours.toFixed(1)}ч`}
              color="bg-purple-600"
              icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
            />
            <KPICard
              title="Затраты"
              value={`$${domainStats.domain.total_cost_usd.toFixed(2)}`}
              color="bg-yellow-600"
              icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
            />
          </div>

          {/* Meeting Types */}
          <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200">
            <h3 className="text-lg font-semibold text-slate-800 mb-4">Типы встреч</h3>
            {domainStats.domain.meeting_types.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-slate-500 text-sm">
                      <th className="pb-3">Тип</th>
                      <th className="pb-3 text-center">Всего</th>
                      <th className="pb-3 text-center">Успешно</th>
                      <th className="pb-3 text-center">Ошибки</th>
                      <th className="pb-3 text-center">Успешность</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {domainStats.domain.meeting_types.map(mt => (
                      <tr key={mt.meeting_type} className="text-slate-800">
                        <td className="py-3">{mt.name}</td>
                        <td className="py-3 text-center">{mt.count}</td>
                        <td className="py-3 text-center text-green-600">{mt.completed}</td>
                        <td className="py-3 text-center text-red-600">{mt.failed}</td>
                        <td className="py-3 text-center">
                          <span className={`px-2 py-1 rounded text-xs ${
                            mt.success_rate >= 90 ? 'bg-green-100 text-green-700' :
                            mt.success_rate >= 70 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'
                          }`}>
                            {mt.success_rate.toFixed(1)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-slate-400 text-center py-4">Нет данных о типах встреч</p>
            )}
          </div>

          {/* Projects (for construction) */}
          {domainStats.projects && domainStats.projects.projects.length > 0 && (
            <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200">
              <h3 className="text-lg font-semibold text-slate-800 mb-4">
                Проекты ({domainStats.projects.total_projects})
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-slate-500 text-sm">
                      <th className="pb-3">Проект</th>
                      <th className="pb-3">Код</th>
                      <th className="pb-3 text-center">Обработок</th>
                      <th className="pb-3 text-center">Успешность</th>
                      <th className="pb-3 text-center">Последняя активность</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {domainStats.projects.projects.map(p => (
                      <tr key={p.project_id} className="text-slate-800">
                        <td className="py-3">{p.project_name}</td>
                        <td className="py-3 text-slate-500">{p.project_code}</td>
                        <td className="py-3 text-center">{p.total_jobs}</td>
                        <td className="py-3 text-center">
                          <span className={`px-2 py-1 rounded text-xs ${
                            p.success_rate >= 90 ? 'bg-green-100 text-green-700' :
                            p.success_rate >= 70 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'
                          }`}>
                            {p.success_rate.toFixed(1)}%
                          </span>
                        </td>
                        <td className="py-3 text-center text-slate-500 text-sm">
                          {p.last_activity ? new Date(p.last_activity).toLocaleDateString('ru-RU') : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-severin-red"></div>
        </div>
      )}
    </div>
  );
}

// Users Tab
function UsersTab({ dashboard }: { dashboard: FullDashboardResponse }) {
  const { users } = dashboard;

  return (
    <div className="space-y-6">
      {/* User KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Всего пользователей"
          value={users.total_users}
          color="bg-blue-600"
          icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>}
        />
        <KPICard
          title="Активных"
          value={users.active_users}
          subtitle={`${users.total_users > 0 ? ((users.active_users / users.total_users) * 100).toFixed(1) : 0}% от всех`}
          color="bg-green-600"
          icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* By Role */}
        <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">По ролям</h3>
          {Object.entries(users.by_role).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(users.by_role).map(([role, count]) => (
                <div key={role} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-slate-600 capitalize">{role}</span>
                  <span className="text-slate-800 font-medium">{count}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-400 text-center py-4">Нет данных</p>
          )}
        </div>

        {/* By Domain */}
        <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">По доменам</h3>
          {Object.entries(users.by_domain).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(users.by_domain).map(([domain, count]) => (
                <div key={domain} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-slate-600">{domain || 'Без домена'}</span>
                  <span className="text-slate-800 font-medium">{count}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-400 text-center py-4">Нет данных</p>
          )}
        </div>
      </div>

      {/* Top Users */}
      <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Топ пользователей по активности</h3>
        {users.top_users.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-slate-500 text-sm">
                  <th className="pb-3">Пользователь</th>
                  <th className="pb-3">Роль</th>
                  <th className="pb-3 text-center">Обработок</th>
                  <th className="pb-3 text-center">Успешно</th>
                  <th className="pb-3">Домены</th>
                  <th className="pb-3">Последняя активность</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {users.top_users.map(u => (
                  <tr key={u.user_id} className="text-slate-800">
                    <td className="py-3">
                      <div>
                        <p className="font-medium">{u.full_name || u.email}</p>
                        {u.full_name && <p className="text-slate-500 text-sm">{u.email}</p>}
                      </div>
                    </td>
                    <td className="py-3">
                      <span className="px-2 py-1 bg-slate-100 rounded text-xs capitalize">{u.role}</span>
                    </td>
                    <td className="py-3 text-center">{u.total_jobs}</td>
                    <td className="py-3 text-center text-green-600">{u.completed_jobs}</td>
                    <td className="py-3">
                      <div className="flex flex-wrap gap-1">
                        {u.domains_used.map(d => (
                          <span key={d} className="px-2 py-0.5 bg-red-50 text-severin-red rounded text-xs">
                            {d}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3 text-slate-500 text-sm">
                      {u.last_activity ? new Date(u.last_activity).toLocaleDateString('ru-RU') : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-slate-400 text-center py-4">Нет данных об активности пользователей</p>
        )}
      </div>
    </div>
  );
}

// Costs Tab
function CostsTab({ costStats, dashboard }: { costStats: CostStatsResponse | null; dashboard: FullDashboardResponse | null }) {
  const costs = costStats?.costs || dashboard?.costs;

  if (!costs) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-severin-red"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Cost KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Общие затраты"
          value={`$${costs.total_cost_usd.toFixed(2)}`}
          subtitle={`Flash: $${(costs.flash_cost_usd ?? 0).toFixed(2)} / Pro: $${(costs.pro_cost_usd ?? 0).toFixed(2)}`}
          color="bg-yellow-600"
          icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <KPICard
          title="Средняя стоимость"
          value={`$${costs.avg_cost_per_job.toFixed(4)}`}
          subtitle="За одну обработку"
          color="bg-blue-600"
          icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>}
        />
        <KPICard
          title="Input токены"
          value={costs.total_input_tokens.toLocaleString('ru-RU')}
          subtitle={`Flash: ${(costs.flash_input_tokens ?? 0).toLocaleString('ru-RU')} / Pro: ${(costs.pro_input_tokens ?? 0).toLocaleString('ru-RU')}`}
          color="bg-purple-600"
          icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" /></svg>}
        />
        <KPICard
          title="Output токены"
          value={costs.total_output_tokens.toLocaleString('ru-RU')}
          subtitle={`Flash: ${(costs.flash_output_tokens ?? 0).toLocaleString('ru-RU')} / Pro: ${(costs.pro_output_tokens ?? 0).toLocaleString('ru-RU')}`}
          color="bg-green-600"
          icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Costs by Domain */}
        <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Затраты по доменам</h3>
          {Object.entries(costs.by_domain).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(costs.by_domain).map(([domain, cost]) => (
                <div key={domain} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-slate-600 capitalize">{domain}</span>
                  <span className="text-slate-800 font-medium">${(cost as number).toFixed(2)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-400 text-center py-4">Нет данных</p>
          )}
        </div>

        {/* Pricing Info */}
        <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Тарификация Gemini</h3>
          <div className="space-y-3">
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-100">
              <p className="text-slate-700 text-sm font-semibold mb-2">Gemini 2.5 Flash <span className="text-slate-400 font-normal">— перевод</span></p>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Input</span>
                <span className="text-slate-700">${costs.flash_input_price ?? 0.30} / 1M</span>
              </div>
              <div className="flex justify-between text-sm mt-1">
                <span className="text-slate-500">Output</span>
                <span className="text-slate-700">${costs.flash_output_price ?? 2.50} / 1M</span>
              </div>
            </div>
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-100">
              <p className="text-slate-700 text-sm font-semibold mb-2">Gemini 2.5 Pro <span className="text-slate-400 font-normal">— отчёты, анализ</span></p>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Input</span>
                <span className="text-slate-700">${costs.pro_input_price ?? 1.25} / 1M</span>
              </div>
              <div className="flex justify-between text-sm mt-1">
                <span className="text-slate-500">Output</span>
                <span className="text-slate-700">${costs.pro_output_price ?? 10.00} / 1M</span>
              </div>
            </div>
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-blue-600 text-xs">
                Стоимость считается точно по каждой модели из usage_metadata Gemini API.{' '}
                <a href="https://ai.google.dev/gemini-api/docs/pricing" target="_blank" rel="noopener noreferrer" className="underline hover:text-blue-800">
                  Актуальные тарифы
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
