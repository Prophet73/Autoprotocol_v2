import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import ruLocale from '@fullcalendar/core/locales/ru';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import {
  LayoutDashboard,
  FileText,
  AlertTriangle,
  Flame,
  Search,
  ChevronLeft,
  ChevronRight,
  X,
  Download,
  CheckCircle,
  Loader2,
  Calendar,
  Shield,
} from 'lucide-react';
import {
  getManagerDashboardView,
  getAnalyticsDetail,
  updateProblemStatus,
  downloadAnalyticsReport,
  downloadAnalyticsReportAll,
  type ProjectHealth,
  type AttentionItem,
  type AnalyticsDetail,
} from '../api/client';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

// Health status colors
const healthColors = {
  critical: { bg: 'bg-red-500', text: 'text-red-600', light: 'bg-red-50' },
  attention: { bg: 'bg-amber-500', text: 'text-amber-600', light: 'bg-amber-50' },
  stable: { bg: 'bg-green-500', text: 'text-green-600', light: 'bg-green-50' },
};

export function ManagerDashboardPage() {
  const queryClient = useQueryClient();
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [projectSearch, setProjectSearch] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedAnalyticsId, setSelectedAnalyticsId] = useState<number | null>(null);

  // Fetch dashboard data
  const { data: dashboard, isLoading, error } = useQuery({
    queryKey: ['manager-dashboard', selectedProjectId],
    queryFn: () => getManagerDashboardView(selectedProjectId || undefined),
  });

  // Fetch analytics detail when modal is open
  const { data: analyticsDetail, isLoading: analyticsLoading } = useQuery({
    queryKey: ['analytics-detail', selectedAnalyticsId],
    queryFn: () => getAnalyticsDetail(selectedAnalyticsId!),
    enabled: !!selectedAnalyticsId,
  });

  // Mutation for updating problem status
  const problemMutation = useMutation({
    mutationFn: ({ problemId, status }: { problemId: number; status: 'new' | 'done' }) =>
      updateProblemStatus(problemId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manager-dashboard'] });
    },
  });

  // Filter projects by search and selection
  // When a project is selected, show ONLY that project (others "disappear")
  const filteredProjects = useMemo(() => {
    if (!dashboard?.projects_health) return [];

    // If a project is selected, show only that project
    if (selectedProjectId !== null) {
      return dashboard.projects_health.filter(p => p.id === selectedProjectId);
    }

    // Otherwise, apply search filter
    if (!projectSearch) return dashboard.projects_health;
    const search = projectSearch.toLowerCase();
    return dashboard.projects_health.filter(
      (p) =>
        p.name.toLowerCase().includes(search) ||
        p.project_code.toLowerCase().includes(search)
    );
  }, [dashboard?.projects_health, projectSearch, selectedProjectId]);

  // Calendar events for FullCalendar
  // Format: [project_code] project_name - event title
  const calendarEvents = useMemo(() => {
    if (!dashboard?.calendar_events) return [];
    return dashboard.calendar_events.map((event) => ({
      id: event.id.toString(),
      title: `[${event.project_code}] ${event.project_name} - ${event.title}`,
      date: event.date,
      backgroundColor:
        event.status === 'critical'
          ? '#dc3545'
          : event.status === 'attention'
          ? '#ffc107'
          : '#28a745',
      borderColor: 'transparent',
      extendedProps: { ...event },
    }));
  }, [dashboard?.calendar_events]);

  // Pulse chart data
  const pulseChartData = useMemo(() => {
    if (!dashboard?.pulse_chart) return null;
    return {
      labels: dashboard.pulse_chart.labels,
      datasets: [
        {
          label: 'Критические',
          data: dashboard.pulse_chart.critical,
          backgroundColor: '#dc3545',
        },
        {
          label: 'Требуют внимания',
          data: dashboard.pulse_chart.attention,
          backgroundColor: '#ffc107',
        },
        {
          label: 'Стабильные',
          data: dashboard.pulse_chart.stable,
          backgroundColor: '#28a745',
        },
      ],
    };
  }, [dashboard?.pulse_chart]);

  // Sort attention items: new first, done at bottom
  // IMPORTANT: This hook must be BEFORE any early returns!
  const sortedAttentionItems = useMemo(() => {
    if (!dashboard?.attention_items) return [];
    return [...dashboard.attention_items].sort((a, b) => {
      if (a.status === 'done' && b.status !== 'done') return 1;
      if (a.status !== 'done' && b.status === 'done') return -1;
      // Within same status, sort by severity (critical first)
      if (a.severity === 'critical' && b.severity !== 'critical') return -1;
      if (a.severity !== 'critical' && b.severity === 'critical') return 1;
      return 0;
    });
  }, [dashboard?.attention_items]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[600px]">
        <Loader2 className="w-10 h-10 text-severin-red animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
          <h2 className="font-semibold mb-2">Ошибка загрузки дашборда</h2>
          <p className="text-sm">Не удалось загрузить данные. Попробуйте обновить страницу.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-hidden">
      <div className="grid h-full" style={{
        gridTemplateColumns: sidebarCollapsed ? '60px 1fr' : '300px 1fr'
      }}>
        {/* Left Column - Projects */}
        <div className="bg-white border-r border-slate-200 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            {!sidebarCollapsed && (
              <h2 className="font-semibold text-slate-800">Мои проекты</h2>
            )}
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="p-1.5 hover:bg-slate-100 rounded-lg transition-colors"
            >
              {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </button>
          </div>

          {/* Search */}
          {!sidebarCollapsed && (
            <div className="p-3 border-b border-slate-100">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Поиск..."
                  value={projectSearch}
                  onChange={(e) => setProjectSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-severin-red/20 focus:border-severin-red"
                />
              </div>
            </div>
          )}

          {/* All Projects Button */}
          <button
            onClick={() => setSelectedProjectId(null)}
            className={`m-3 p-3 rounded-lg text-left transition-all ${
              selectedProjectId === null
                ? 'bg-severin-red text-white'
                : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }`}
          >
            {sidebarCollapsed ? (
              <LayoutDashboard className="w-5 h-5 mx-auto" />
            ) : (
              <div className="flex items-center gap-2">
                <LayoutDashboard className="w-5 h-5" />
                <span className="font-medium">Все проекты</span>
              </div>
            )}
          </button>

          {/* Projects List */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {filteredProjects.map((project) => (
              <ProjectItem
                key={project.id}
                project={project}
                isSelected={selectedProjectId === project.id}
                collapsed={sidebarCollapsed}
                onClick={() => setSelectedProjectId(project.id)}
              />
            ))}
          </div>
        </div>

        {/* Center Column - Main Content */}
        <div className="bg-slate-50 overflow-y-auto">
          {/* Dashboard Header */}
          <div className="bg-white border-b border-slate-200 px-6 py-4">
            <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-3">
              <LayoutDashboard className="w-7 h-7 text-severin-red" />
              {selectedProjectId
                ? dashboard?.projects_health?.find(p => p.id === selectedProjectId)?.name || 'Проект'
                : 'Панель управления'}
            </h1>
            {selectedProjectId && (
              <p className="text-sm text-slate-500 mt-1">
                Код проекта: {dashboard?.projects_health?.find(p => p.id === selectedProjectId)?.project_code}
              </p>
            )}
          </div>

          <div className="p-6">
            {/* KPI Cards */}
            {dashboard?.kpi && (
              <div className="grid grid-cols-3 gap-4 mb-6">
                <KPICard
                  label="Всего отчётов"
                  value={dashboard.kpi.total_jobs}
                  icon={FileText}
                  color="slate"
                />
                <KPICard
                  label="Требуют внимания"
                  value={dashboard.kpi.attention_jobs}
                  icon={AlertTriangle}
                  color="amber"
                />
                <KPICard
                  label="Критические"
                  value={dashboard.kpi.critical_jobs}
                  icon={Flame}
                  color="red"
                />
              </div>
            )}

          {/* Calendar or Pulse Chart */}
          {selectedProjectId === null ? (
            // Show Calendar for all projects
            <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6">
              <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-severin-red" />
                Календарь отчётов
              </h3>
              <FullCalendar
                plugins={[dayGridPlugin, interactionPlugin]}
                initialView="dayGridMonth"
                events={calendarEvents}
                locales={[ruLocale]}
                locale="ru"
                headerToolbar={{
                  left: 'prev,next today',
                  center: 'title',
                  right: 'dayGridMonth,dayGridWeek',
                }}
                buttonText={{
                  today: 'Сегодня',
                  month: 'Месяц',
                  week: 'Неделя',
                }}
                eventClick={(info) => {
                  const analyticsId = info.event.extendedProps.analytics_id;
                  if (analyticsId) {
                    setSelectedAnalyticsId(analyticsId);
                  }
                }}
                height="auto"
                contentHeight={450}
              />
            </div>
          ) : (
            // Show Pulse Chart for specific project
            pulseChartData && (
              <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6">
                <h3 className="font-semibold text-slate-800 mb-4">Пульс проекта</h3>
                <div style={{ height: 350 }}>
                  <Bar
                    data={pulseChartData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: { position: 'top' },
                      },
                      scales: {
                        x: { stacked: true },
                        y: { stacked: true },
                      },
                    }}
                  />
                </div>
              </div>
            )
          )}

          {/* Attention Items / Triage */}
          {sortedAttentionItems.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="p-4 border-b border-slate-100">
                <h3 className="font-semibold text-slate-800">Требуют внимания</h3>
              </div>
              <div className="divide-y divide-slate-100 max-h-[500px] overflow-y-auto">
                {sortedAttentionItems.map((item) => (
                  <AttentionItemRow
                    key={item.id}
                    item={item}
                    onStatusChange={(status) =>
                      problemMutation.mutate({ problemId: item.id, status })
                    }
                    onViewDetails={() => setSelectedAnalyticsId(item.analytics_id)}
                  />
                ))}
              </div>
            </div>
          )}
          </div>
        </div>
      </div>

      {/* Analytics Detail Modal */}
      {selectedAnalyticsId && (
        <AnalyticsModal
          analyticsId={selectedAnalyticsId}
          detail={analyticsDetail}
          isLoading={analyticsLoading}
          onClose={() => setSelectedAnalyticsId(null)}
        />
      )}
    </div>
  );
}

// Project Item Component
function ProjectItem({
  project,
  isSelected,
  collapsed,
  onClick,
}: {
  project: ProjectHealth;
  isSelected: boolean;
  collapsed: boolean;
  onClick: () => void;
}) {
  const colors = healthColors[project.health];

  if (collapsed) {
    return (
      <button
        onClick={onClick}
        className={`w-full p-2 rounded-lg transition-all ${
          isSelected ? 'bg-red-50 ring-2 ring-severin-red' : 'hover:bg-slate-100'
        }`}
        title={project.name}
      >
        <div className={`w-3 h-3 rounded-full ${colors.bg} mx-auto`} />
      </button>
    );
  }

  return (
    <button
      onClick={onClick}
      className={`w-full p-3 rounded-lg text-left transition-all ${
        isSelected
          ? 'bg-red-50 ring-2 ring-severin-red'
          : 'hover:bg-slate-100'
      }`}
    >
      <div className="flex items-center gap-3">
        <div className={`w-3 h-3 rounded-full ${colors.bg} flex-shrink-0`} />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-slate-800 truncate">{project.name}</p>
          <p className="text-xs text-slate-500">{project.project_code}</p>
        </div>
      </div>
      {project.open_issues > 0 && (
        <div className="mt-2 text-xs text-amber-600">
          {project.open_issues} открытых проблем
        </div>
      )}
    </button>
  );
}

// KPI Card Component
function KPICard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: number;
  icon: React.ElementType;
  color: 'slate' | 'amber' | 'red';
}) {
  const colorClasses = {
    slate: 'bg-slate-100 text-slate-600',
    amber: 'bg-amber-100 text-amber-600',
    red: 'bg-red-100 text-red-600',
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg ${colorClasses[color]} flex items-center justify-center`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-bold text-slate-800">{value}</p>
          <p className="text-sm text-slate-500">{label}</p>
        </div>
      </div>
    </div>
  );
}

// Attention Item Row Component
function AttentionItemRow({
  item,
  onStatusChange,
  onViewDetails,
}: {
  item: AttentionItem;
  onStatusChange: (status: 'new' | 'done') => void;
  onViewDetails: () => void;
}) {
  const isCritical = item.severity === 'critical';
  const isDone = item.status === 'done';

  return (
    <div className={`p-4 flex items-start gap-3 transition-colors ${
      isDone ? 'bg-slate-50 opacity-60' : 'hover:bg-slate-50'
    }`}>
      <div className={`mt-1 ${
        isDone ? 'text-slate-400' : isCritical ? 'text-red-500' : 'text-amber-500'
      }`}>
        {isCritical ? <Flame className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
      </div>
      <div className="flex-1 min-w-0">
        <button
          onClick={onViewDetails}
          className={`text-left font-medium transition-colors ${
            isDone
              ? 'text-slate-400 line-through'
              : 'text-slate-800 hover:text-severin-red'
          }`}
        >
          {item.problem_text}
        </button>
        <p className={`text-sm truncate mt-1 ${isDone ? 'text-slate-400' : 'text-slate-500'}`}>
          {item.project_name} • {item.source_file}
        </p>
      </div>
      <input
        type="checkbox"
        checked={isDone}
        onChange={(e) => onStatusChange(e.target.checked ? 'done' : 'new')}
        className="w-5 h-5 rounded border-slate-300 text-severin-red focus:ring-severin-red"
      />
    </div>
  );
}

// Get status color for indicator
function getIndicatorStatusColor(status: string): { bg: string; text: string } {
  const statusLower = status.toLowerCase();
  if (statusLower.includes('критич')) {
    return { bg: 'bg-red-100', text: 'text-red-700' };
  } else if (statusLower.includes('риск')) {
    return { bg: 'bg-amber-100', text: 'text-amber-700' };
  }
  return { bg: 'bg-green-100', text: 'text-green-700' };
}

// Analytics Modal Component - Autoprotocol format with brief type switcher
function AnalyticsModal({
  analyticsId,
  detail,
  isLoading,
  onClose,
}: {
  analyticsId: number;
  detail?: AnalyticsDetail;
  isLoading: boolean;
  onClose: () => void;
}) {
  // Brief type state: 'manager' or 'risk'
  const [briefType, setBriefType] = useState<'manager' | 'risk'>('manager');

  // Parse toxicity details (format: "Level\n\nComment")
  const toxicityParts = detail?.toxicity_details?.split('\n\n') || [];
  const toxicityLevel = toxicityParts[0] || 'Нейтральный';
  const toxicityComment = toxicityParts.slice(1).join('\n\n') || detail?.toxicity_details || '';

  // Get status badge color
  const getStatusBadge = (status: string) => {
    const statusLower = status.toLowerCase();
    if (statusLower.includes('критич')) return 'bg-red-500 text-white';
    if (statusLower.includes('внимания') || statusLower.includes('риск')) return 'bg-amber-500 text-white';
    return 'bg-green-500 text-white';
  };

  // Check if risk brief is available
  const hasRiskBrief = detail?.has_risk_brief ?? false;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl w-[95vw] max-w-[1600px] h-[92vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <div>
                <h2 className="text-xl font-bold text-slate-800">
                  {briefType === 'manager' ? 'Менеджерский бриф' : 'Риск-бриф'}
                </h2>
                {detail?.filename && (
                  <p className="text-sm text-slate-500 mt-1">{detail.filename}</p>
                )}
              </div>
              {detail?.status && (
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusBadge(detail.status)}`}>
                  {detail.status === 'critical' ? 'Критический' :
                   detail.status === 'attention' ? 'Требует внимания' : 'Стабильный'}
                </span>
              )}
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-200 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Tab Switcher - only show if risk brief is available */}
          {hasRiskBrief && (
            <div className="flex gap-2">
              <button
                onClick={() => setBriefType('manager')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                  briefType === 'manager'
                    ? 'bg-severin-red text-white'
                    : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
                }`}
              >
                <FileText className="w-4 h-4" />
                Менеджерский бриф
              </button>
              <button
                onClick={() => setBriefType('risk')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                  briefType === 'risk'
                    ? 'bg-severin-red text-white'
                    : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
                }`}
              >
                <Shield className="w-4 h-4" />
                Риск-бриф
              </button>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-severin-red animate-spin" />
            </div>
          ) : detail ? (
            <div className="space-y-6">
              {/* Risk Brief View */}
              {briefType === 'risk' ? (
                <div className="text-center py-8">
                  <div className="w-20 h-20 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-6">
                    <Shield className="w-10 h-10 text-severin-red" />
                  </div>
                  <h3 className="text-xl font-semibold text-slate-800 mb-3">
                    Риск-бриф для инвестора
                  </h3>
                  <p className="text-slate-600 mb-6 max-w-md mx-auto">
                    Детальный анализ рисков проекта с матрицей P×I,
                    классификацией по категориям и рекомендациями по митигации.
                  </p>
                  <button
                    onClick={() => downloadAnalyticsReport(analyticsId, 'risk_brief')}
                    className="px-6 py-3 bg-severin-red text-white rounded-lg hover:bg-severin-red-dark transition-colors flex items-center gap-2 font-medium shadow-lg mx-auto cursor-pointer"
                  >
                    <Download className="w-5 h-5" />
                    Скачать риск-бриф (PDF)
                  </button>
                </div>
              ) : (
                <>
                  {/* Manager Brief View - Executive Summary */}
                  <div className="bg-slate-50 rounded-lg p-4">
                    <h3 className="font-semibold text-slate-800 mb-2 flex items-center gap-2">
                      <FileText className="w-5 h-5 text-severin-red" />
                      Выжимка для руководителя
                    </h3>
                    <p className="text-slate-700 leading-relaxed">{detail.summary}</p>
                  </div>

                  {/* Panel of Project Status - Table format */}
                  {detail.key_indicators.length > 0 && (
                    <div>
                      <h3 className="font-semibold text-slate-800 mb-3">Панель состояния проекта</h3>
                      <div className="border border-slate-200 rounded-lg overflow-hidden">
                        <table className="w-full">
                          <thead className="bg-slate-50">
                            <tr>
                              <th className="text-left px-4 py-2 text-sm font-semibold text-slate-600 border-b">Показатель</th>
                              <th className="text-left px-4 py-2 text-sm font-semibold text-slate-600 border-b w-28">Статус</th>
                              <th className="text-left px-4 py-2 text-sm font-semibold text-slate-600 border-b">Комментарий AI</th>
                            </tr>
                          </thead>
                          <tbody>
                            {detail.key_indicators.map((indicator, idx) => {
                              const colors = getIndicatorStatusColor(indicator.status);
                              return (
                                <tr key={idx} className="border-b last:border-b-0 hover:bg-slate-50">
                                  <td className="px-4 py-3 text-slate-800 font-medium">{indicator.indicator_name}</td>
                                  <td className="px-4 py-3">
                                    <span className={`px-2 py-1 rounded text-xs font-medium ${colors.bg} ${colors.text}`}>
                                      {indicator.status}
                                    </span>
                                  </td>
                                  <td className="px-4 py-3 text-sm text-slate-600">{indicator.comment}</td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Key Challenges and Recommendations */}
                  {detail.challenges.length > 0 && (
                    <div>
                      <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5 text-amber-500" />
                        Ключевые проблемы и рекомендации
                      </h3>
                      <div className="space-y-3">
                        {detail.challenges.map((challenge, idx) => (
                          <div key={idx} className="p-4 bg-amber-50 border-l-4 border-amber-400 rounded-r-lg">
                            <p className="text-slate-800 mb-2">{challenge.text}</p>
                            <p className="text-sm text-amber-800 bg-amber-100/50 px-3 py-2 rounded">
                              <span className="font-semibold">Рекомендация:</span> {challenge.recommendation}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Key Achievements */}
                  {detail.achievements.length > 0 && (
                    <div>
                      <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                        <CheckCircle className="w-5 h-5 text-green-500" />
                        Важные достижения и возможности
                      </h3>
                      <ul className="space-y-2">
                        {detail.achievements.map((achievement, idx) => (
                          <li key={idx} className="flex items-start gap-3 p-3 bg-green-50 rounded-lg">
                            <div className="w-2 h-2 bg-green-500 rounded-full mt-2 flex-shrink-0" />
                            <p className="text-slate-700">{achievement}</p>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Toxicity Meter - Atmosphere Analysis */}
                  {detail.toxicity_level !== undefined && (
                    <div>
                      <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                        <Flame className="w-5 h-5 text-orange-500" />
                        Анализ атмосферы ("Токсикометр")
                      </h3>
                      <div className="p-4 bg-slate-50 rounded-lg">
                        <div className="flex items-center gap-4 mb-3">
                          <span className="text-sm text-slate-500">Общий уровень:</span>
                          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                            detail.toxicity_level > 60 ? 'bg-red-100 text-red-700' :
                            detail.toxicity_level > 30 ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'
                          }`}>
                            {toxicityLevel}
                          </span>
                          <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                            <div
                              className={`h-full transition-all ${
                                detail.toxicity_level > 60 ? 'bg-red-500' :
                                detail.toxicity_level > 30 ? 'bg-amber-500' : 'bg-green-500'
                              }`}
                              style={{ width: `${detail.toxicity_level}%` }}
                            />
                          </div>
                        </div>
                        <p className="text-sm text-slate-600">{toxicityComment}</p>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          ) : (
            <div className="text-center text-slate-500 py-12">
              Данные не найдены
            </div>
          )}
        </div>

        {/* Footer with download buttons - updated format (no transcript, has risk brief) */}
        {(detail?.has_main_report || detail?.has_tasks || detail?.has_risk_brief) && (
          <div className="p-4 border-t border-slate-200 bg-slate-50 flex flex-wrap justify-end gap-3">
            <button
              onClick={() => downloadAnalyticsReportAll(analyticsId)}
              className="px-5 py-2.5 bg-slate-800 text-white rounded-lg hover:bg-slate-900 transition-colors flex items-center gap-2 font-medium shadow-sm cursor-pointer"
            >
              <Download className="w-4 h-4" />
              Скачать все файлы
            </button>
            {detail.has_main_report && (
              <button
                onClick={() => downloadAnalyticsReport(analyticsId, 'main')}
                className="px-5 py-2.5 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition-colors flex items-center gap-2 font-medium shadow-sm cursor-pointer"
              >
                <Download className="w-4 h-4" />
                Скачать отчёт (DOCX)
              </button>
            )}
            {detail.has_tasks && (
              <button
                onClick={() => downloadAnalyticsReport(analyticsId, 'tasks')}
                className="px-5 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors flex items-center gap-2 font-medium shadow-sm cursor-pointer"
              >
                <Download className="w-4 h-4" />
                Скачать задачи (XLSX)
              </button>
            )}
            {detail.has_risk_brief && (
              <button
                onClick={() => downloadAnalyticsReport(analyticsId, 'risk_brief')}
                className="px-5 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2 font-medium shadow-sm cursor-pointer"
              >
                <Shield className="w-4 h-4" />
                Скачать риск-бриф (PDF)
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
