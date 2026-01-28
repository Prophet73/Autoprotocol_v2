import { useEffect, useState, useMemo } from 'react';
import {
  comprehensiveStatsApi,
  type FullDashboardResponse,
  type StatsFilters,
  type DomainInfo,
  type DomainStatsResponse,
  type CostStatsResponse,
} from '../../api/adminApi';

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
    <div className="bg-gray-800 rounded-lg p-5">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-gray-400 text-sm">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
          {subtitle && <p className="text-gray-500 text-xs mt-1">{subtitle}</p>}
          {trend && (
            <div className={`flex items-center mt-2 text-xs ${trend.positive ? 'text-green-400' : 'text-red-400'}`}>
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
        <span className="text-gray-300">{label}</span>
        <span className="text-white">{value}</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${Math.min(percentage, 100)}%` }} />
      </div>
    </div>
  );
}

// Simple bar chart component
function BarChart({ data, height = 150 }: { data: Array<{ label: string; value: number }>; height?: number }) {
  const maxValue = Math.max(...data.map(d => d.value), 1);

  return (
    <div className="flex items-end justify-between gap-1" style={{ height }}>
      {data.map((item, idx) => (
        <div key={idx} className="flex-1 flex flex-col items-center">
          <div
            className="w-full bg-blue-500 rounded-t transition-all hover:bg-blue-400"
            style={{ height: `${(item.value / maxValue) * 100}%`, minHeight: item.value > 0 ? 4 : 0 }}
            title={`${item.label}: ${item.value}`}
          />
          <span className="text-xs text-gray-500 mt-1 truncate w-full text-center">{item.label}</span>
        </div>
      ))}
    </div>
  );
}

export default function StatsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Data states
  const [dashboard, setDashboard] = useState<FullDashboardResponse | null>(null);
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<string>('');
  const [domainStats, setDomainStats] = useState<DomainStatsResponse | null>(null);
  const [costStats, setCostStats] = useState<CostStatsResponse | null>(null);

  // Filters
  const [filters, setFilters] = useState<StatsFilters>({});
  const [dateFrom, setDateFrom] = useState('');
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
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки статистики');
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

  // Timeline chart data
  const timelineData = useMemo(() => {
    if (!dashboard?.timeline?.points) return [];
    return dashboard.timeline.points.slice(-14).map(p => ({
      label: new Date(p.date).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }),
      value: p.jobs,
    }));
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
      <div className="bg-red-900/50 border border-red-500 rounded-lg p-4">
        <p className="text-red-400">{error}</p>
        <button onClick={loadDashboard} className="mt-2 text-sm text-red-300 hover:text-red-200 underline">
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
          <h1 className="text-2xl font-bold text-white">Статистика</h1>
          <p className="text-gray-400 mt-1">Аналитика и отчёты</p>
        </div>
        <button
          onClick={loadDashboard}
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition flex items-center self-start"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Обновить
        </button>
      </div>

      {/* Filters */}
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Период с</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">по</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Домен</label>
            <select
              value={filters.domain || ''}
              onChange={(e) => setFilters({ ...filters, domain: e.target.value || undefined })}
              className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="">Все домены</option>
              {domains.map(d => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>
          <button
            onClick={applyFilters}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm transition"
          >
            Применить
          </button>
          <button
            onClick={clearFilters}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm transition"
          >
            Сбросить
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-700">
        <nav className="flex space-x-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-white hover:border-gray-600'
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
        <OverviewTab dashboard={dashboard} timelineData={timelineData} />
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
        <div className="text-center text-gray-500 text-sm">
          Данные обновлены: {new Date(dashboard.generated_at).toLocaleString('ru-RU')}
        </div>
      )}
    </div>
  );
}

// Overview Tab
function OverviewTab({ dashboard, timelineData }: { dashboard: FullDashboardResponse; timelineData: Array<{ label: string; value: number }> }) {
  const { overview, domains, artifacts, errors } = dashboard;

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
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
          title="Время обработки"
          value={`${overview.total_processing_hours.toFixed(1)}ч`}
          subtitle={`Среднее: ${overview.avg_processing_minutes.toFixed(1)} мин`}
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Timeline chart */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Обработки за период</h3>
          {timelineData.length > 0 ? (
            <BarChart data={timelineData} height={180} />
          ) : (
            <p className="text-gray-500 text-center py-8">Нет данных за выбранный период</p>
          )}
        </div>

        {/* Domains breakdown */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">По доменам</h3>
          {domains.domains.length > 0 ? (
            <div className="space-y-4">
              {domains.domains.map(d => (
                <div key={d.domain} className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg">
                  <div>
                    <p className="text-white font-medium">{d.display_name}</p>
                    <p className="text-gray-400 text-sm">{d.total_jobs} обработок</p>
                  </div>
                  <div className="text-right">
                    <p className={`font-medium ${d.success_rate >= 90 ? 'text-green-400' : d.success_rate >= 70 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {d.success_rate.toFixed(1)}%
                    </p>
                    <p className="text-gray-400 text-sm">${d.total_cost_usd.toFixed(2)}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">Нет данных</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Artifacts */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Артефакты</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center p-4 bg-gray-700/50 rounded-lg">
              <p className="text-2xl font-bold text-white">{artifacts.transcripts_generated}</p>
              <p className="text-gray-400 text-sm">Транскриптов</p>
              <p className="text-blue-400 text-xs">{artifacts.transcript_rate.toFixed(1)}%</p>
            </div>
            <div className="text-center p-4 bg-gray-700/50 rounded-lg">
              <p className="text-2xl font-bold text-white">{artifacts.tasks_generated}</p>
              <p className="text-gray-400 text-sm">Задач</p>
              <p className="text-blue-400 text-xs">{artifacts.tasks_rate.toFixed(1)}%</p>
            </div>
            <div className="text-center p-4 bg-gray-700/50 rounded-lg">
              <p className="text-2xl font-bold text-white">{artifacts.reports_generated}</p>
              <p className="text-gray-400 text-sm">Отчётов</p>
              <p className="text-blue-400 text-xs">{artifacts.report_rate.toFixed(1)}%</p>
            </div>
            <div className="text-center p-4 bg-gray-700/50 rounded-lg">
              <p className="text-2xl font-bold text-white">{artifacts.analysis_generated}</p>
              <p className="text-gray-400 text-sm">Анализов</p>
              <p className="text-blue-400 text-xs">{artifacts.analysis_rate.toFixed(1)}%</p>
            </div>
          </div>
        </div>

        {/* Errors */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Ошибки</h3>
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-3xl font-bold text-red-400">{errors.total_errors}</p>
              <p className="text-gray-400 text-sm">Всего ошибок ({errors.error_rate.toFixed(1)}%)</p>
            </div>
          </div>
          {Object.keys(errors.by_stage).length > 0 && (
            <div>
              <p className="text-sm text-gray-400 mb-2">По этапам:</p>
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
  domains: DomainInfo[];
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
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
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
              title="Время обработки"
              value={`${domainStats.domain.total_processing_hours.toFixed(1)}ч`}
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
          <div className="bg-gray-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Типы встреч</h3>
            {domainStats.domain.meeting_types.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-gray-400 text-sm">
                      <th className="pb-3">Тип</th>
                      <th className="pb-3 text-center">Всего</th>
                      <th className="pb-3 text-center">Успешно</th>
                      <th className="pb-3 text-center">Ошибки</th>
                      <th className="pb-3 text-center">Успешность</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700">
                    {domainStats.domain.meeting_types.map(mt => (
                      <tr key={mt.meeting_type} className="text-white">
                        <td className="py-3">{mt.name}</td>
                        <td className="py-3 text-center">{mt.count}</td>
                        <td className="py-3 text-center text-green-400">{mt.completed}</td>
                        <td className="py-3 text-center text-red-400">{mt.failed}</td>
                        <td className="py-3 text-center">
                          <span className={`px-2 py-1 rounded text-xs ${
                            mt.success_rate >= 90 ? 'bg-green-900 text-green-400' :
                            mt.success_rate >= 70 ? 'bg-yellow-900 text-yellow-400' : 'bg-red-900 text-red-400'
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
              <p className="text-gray-500 text-center py-4">Нет данных о типах встреч</p>
            )}
          </div>

          {/* Projects (for construction) */}
          {domainStats.projects && domainStats.projects.projects.length > 0 && (
            <div className="bg-gray-800 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-white mb-4">
                Проекты ({domainStats.projects.total_projects})
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-gray-400 text-sm">
                      <th className="pb-3">Проект</th>
                      <th className="pb-3">Код</th>
                      <th className="pb-3 text-center">Обработок</th>
                      <th className="pb-3 text-center">Успешность</th>
                      <th className="pb-3 text-center">Последняя активность</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700">
                    {domainStats.projects.projects.map(p => (
                      <tr key={p.project_id} className="text-white">
                        <td className="py-3">{p.project_name}</td>
                        <td className="py-3 text-gray-400">{p.project_code}</td>
                        <td className="py-3 text-center">{p.total_jobs}</td>
                        <td className="py-3 text-center">
                          <span className={`px-2 py-1 rounded text-xs ${
                            p.success_rate >= 90 ? 'bg-green-900 text-green-400' :
                            p.success_rate >= 70 ? 'bg-yellow-900 text-yellow-400' : 'bg-red-900 text-red-400'
                          }`}>
                            {p.success_rate.toFixed(1)}%
                          </span>
                        </td>
                        <td className="py-3 text-center text-gray-400 text-sm">
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
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
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
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">По ролям</h3>
          {Object.entries(users.by_role).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(users.by_role).map(([role, count]) => (
                <div key={role} className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg">
                  <span className="text-gray-300 capitalize">{role}</span>
                  <span className="text-white font-medium">{count}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-4">Нет данных</p>
          )}
        </div>

        {/* By Domain */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">По доменам</h3>
          {Object.entries(users.by_domain).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(users.by_domain).map(([domain, count]) => (
                <div key={domain} className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg">
                  <span className="text-gray-300">{domain || 'Без домена'}</span>
                  <span className="text-white font-medium">{count}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-4">Нет данных</p>
          )}
        </div>
      </div>

      {/* Top Users */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Топ пользователей по активности</h3>
        {users.top_users.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 text-sm">
                  <th className="pb-3">Пользователь</th>
                  <th className="pb-3">Роль</th>
                  <th className="pb-3 text-center">Обработок</th>
                  <th className="pb-3 text-center">Успешно</th>
                  <th className="pb-3">Домены</th>
                  <th className="pb-3">Последняя активность</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {users.top_users.map(u => (
                  <tr key={u.user_id} className="text-white">
                    <td className="py-3">
                      <div>
                        <p className="font-medium">{u.full_name || u.email}</p>
                        {u.full_name && <p className="text-gray-400 text-sm">{u.email}</p>}
                      </div>
                    </td>
                    <td className="py-3">
                      <span className="px-2 py-1 bg-gray-700 rounded text-xs capitalize">{u.role}</span>
                    </td>
                    <td className="py-3 text-center">{u.total_jobs}</td>
                    <td className="py-3 text-center text-green-400">{u.completed_jobs}</td>
                    <td className="py-3">
                      <div className="flex flex-wrap gap-1">
                        {u.domains_used.map(d => (
                          <span key={d} className="px-2 py-0.5 bg-blue-900/50 text-blue-400 rounded text-xs">
                            {d}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3 text-gray-400 text-sm">
                      {u.last_activity ? new Date(u.last_activity).toLocaleDateString('ru-RU') : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-4">Нет данных об активности пользователей</p>
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
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
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
          subtitle={`$${costs.input_price_per_million}/1M`}
          color="bg-purple-600"
          icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" /></svg>}
        />
        <KPICard
          title="Output токены"
          value={costs.total_output_tokens.toLocaleString('ru-RU')}
          subtitle={`$${costs.output_price_per_million}/1M`}
          color="bg-green-600"
          icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Costs by Domain */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Затраты по доменам</h3>
          {Object.entries(costs.by_domain).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(costs.by_domain).map(([domain, cost]) => (
                <div key={domain} className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg">
                  <span className="text-gray-300 capitalize">{domain}</span>
                  <span className="text-white font-medium">${(cost as number).toFixed(2)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-4">Нет данных</p>
          )}
        </div>

        {/* Pricing Info */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Тарификация Gemini</h3>
          <div className="space-y-4">
            <div className="p-4 bg-gray-700/50 rounded-lg">
              <p className="text-gray-400 text-sm mb-1">Gemini Flash 2.0</p>
              <div className="flex justify-between">
                <span className="text-gray-300">Input токены</span>
                <span className="text-white">${costs.input_price_per_million} / 1M</span>
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-gray-300">Output токены</span>
                <span className="text-white">${costs.output_price_per_million} / 1M</span>
              </div>
            </div>
            <div className="p-4 bg-blue-900/30 border border-blue-800 rounded-lg">
              <p className="text-blue-400 text-sm">
                Цены актуальны на момент настройки системы. Проверяйте актуальные тарифы на{' '}
                <a href="https://ai.google.dev/gemini-api/docs/models" target="_blank" rel="noopener noreferrer" className="underline hover:text-blue-300">
                  Google AI
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
