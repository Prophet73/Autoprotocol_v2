import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../stores/authStore';
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
  ChevronDown,
  ChevronUp,
  Download,
  CheckCircle,
  Loader2,
  Calendar,
  Target,
  Clock,
  User,
} from 'lucide-react';
import {
  getManagerDashboardView,
  getAnalyticsDetail,
  updateProblemStatus,
  downloadAnalyticsReport,
  type ProjectHealth,
  type AttentionItem,
  type AnalyticsDetail,
  type ProjectRisk,
  type TaskItem,
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
  const { user } = useAuthStore();
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [projectSearch, setProjectSearch] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedAnalyticsId, setSelectedAnalyticsId] = useState<number | null>(null);

  // Check if user can see full risk brief (manager, admin, superuser)
  const canSeeFullRiskBrief = user?.is_superuser || ['manager', 'admin', 'superuser'].includes(user?.role || '');

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
  // Format: [КОД] Название проекта
  const calendarEvents = useMemo(() => {
    if (!dashboard?.calendar_events) return [];
    return dashboard.calendar_events.map((event) => ({
      id: event.id.toString(),
      title: `[${event.project_code}] ${event.project_name}`,
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
          canSeeFullRiskBrief={canSeeFullRiskBrief}
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

// Risk Card with Accordion for detailed analysis - muted colors
function RiskCard({ risk }: { risk: ProjectRisk }) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Score and severity - muted colors
  const score = risk.probability * risk.impact;
  const getSeverityColor = () => {
    if (score >= 15) return { bg: 'bg-slate-50', border: 'border-l-red-400', badge: 'bg-red-100 text-red-700' };
    if (score >= 9) return { bg: 'bg-slate-50', border: 'border-l-amber-400', badge: 'bg-amber-100 text-amber-700' };
    return { bg: 'bg-slate-50', border: 'border-l-slate-300', badge: 'bg-slate-100 text-slate-600' };
  };
  const colors = getSeverityColor();

  // Category labels
  const categoryLabels: Record<string, string> = {
    external: 'Внешние',
    preinvest: 'Прединвестиционные',
    design: 'Проектные',
    production: 'Строительные',
    management: 'Управленческие',
    operational: 'Эксплуатационные',
    safety: 'Безопасность',
  };

  // Driver type labels
  const driverTypeLabels: Record<string, string> = {
    root_cause: 'Первопричина',
    aggravator: 'Усугубляющий фактор',
    blocker: 'Блокирующий фактор',
  };

  const hasDrivers = risk.drivers && risk.drivers.length > 0;
  // Show AI recommendation whenever it exists (even if there's a decision)
  const hasMitigation = !!risk.mitigation;

  return (
    <div className={`rounded-lg border border-slate-200 ${colors.border} border-l-4 ${colors.bg} overflow-hidden`}>
      {/* Risk Header */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors.badge}`}>
                {risk.id}
              </span>
              <span className="px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-500">
                {categoryLabels[risk.category] || risk.category}
              </span>
              <span className="text-xs text-slate-400">
                {score} баллов
              </span>
            </div>
            <h4 className="font-medium text-slate-800 mb-1">{risk.title}</h4>
            <p className="text-sm text-slate-600">{risk.description}</p>
          </div>
        </div>

        {/* Consequences */}
        {risk.consequences && (
          <div className="mt-3 p-3 bg-white rounded border border-slate-100">
            <span className="text-xs text-slate-400 uppercase">Последствия:</span>
            <p className="text-sm text-slate-600 mt-1">{risk.consequences}</p>
          </div>
        )}

        {/* Decision from meeting - ALWAYS VISIBLE */}
        {risk.decision && (
          <div className="mt-3 p-3 bg-emerald-50 rounded border border-emerald-100">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle className="w-4 h-4 text-emerald-600" />
              <span className="text-xs text-emerald-600 uppercase">Решение:</span>
            </div>
            <p className="text-sm text-slate-700">{risk.decision}</p>
          </div>
        )}

        {/* Responsible and Deadline */}
        {(risk.responsible || risk.deadline) && (
          <div className="mt-3 flex flex-wrap gap-4 text-sm">
            {risk.responsible && (
              <div className="flex items-center gap-1.5 text-slate-500">
                <User className="w-3.5 h-3.5" />
                <span>{risk.responsible}</span>
              </div>
            )}
            {risk.deadline && (
              <div className="flex items-center gap-1.5 text-slate-500">
                <Clock className="w-3.5 h-3.5" />
                <span>{risk.deadline}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Accordion for detailed analysis */}
      {(hasDrivers || hasMitigation) && (
        <>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full px-4 py-2.5 bg-slate-700 hover:bg-slate-800 border-t border-slate-600 flex items-center justify-center gap-2 text-sm text-white font-medium transition-colors cursor-pointer"
          >
            <Target className="w-4 h-4" />
            <span>{isExpanded ? 'Скрыть анализ ИИ' : 'Показать анализ ИИ'}</span>
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {isExpanded && (
            <div className="px-4 pb-4 pt-3 space-y-3 bg-white">
              {/* AI Mitigation recommendation */}
              {hasMitigation && (
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex items-center gap-2 mb-2">
                    <Target className="w-5 h-5 text-blue-600" />
                    <span className="text-sm font-semibold text-blue-800">Рекомендация ИИ</span>
                  </div>
                  <p className="text-slate-700">{risk.mitigation}</p>
                </div>
              )}

              {/* Drivers (root causes, aggravators, blockers) */}
              {hasDrivers && (
                <div className="space-y-2">
                  {risk.drivers.map((driver, idx) => (
                    <div key={idx} className="p-3 bg-slate-50 rounded border border-slate-100">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-mono text-slate-400">{driver.id}</span>
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          driver.type === 'root_cause' ? 'bg-slate-200 text-slate-600' :
                          driver.type === 'aggravator' ? 'bg-slate-200 text-slate-600' :
                          'bg-slate-200 text-slate-600'
                        }`}>
                          {driverTypeLabels[driver.type] || driver.type}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-slate-700">{driver.title}</p>
                      <p className="text-sm text-slate-500 mt-1">{driver.description}</p>
                      {driver.evidence && (
                        <p className="text-xs text-slate-400 mt-2 italic">"{driver.evidence}"</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// Tasks Table Component - compact table view
function TasksTable({ tasks }: { tasks: TaskItem[] }) {
  const priorityText: Record<string, { label: string; color: string }> = {
    high: { label: 'Высокий', color: 'text-red-600' },
    medium: { label: 'Средний', color: 'text-amber-600' },
    low: { label: 'Низкий', color: 'text-slate-400' },
  };

  // Sort by category (like in Excel report), then by priority within category
  const sortedTasks = [...tasks].sort((a, b) => {
    // First sort by category
    const catA = a.category || 'Без категории';
    const catB = b.category || 'Без категории';
    if (catA !== catB) {
      return catA.localeCompare(catB, 'ru');
    }
    // Then by priority within category
    const order = { high: 0, medium: 1, low: 2 };
    return (order[a.priority || 'medium'] || 1) - (order[b.priority || 'medium'] || 1);
  });

  // Group tasks by category for display
  let currentCategory = '';
  let taskNumber = 0;

  return (
    <div className="overflow-x-auto -mx-6">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-slate-100 border-y border-slate-200">
            <th className="py-2.5 pl-6 pr-2 text-left font-medium text-slate-600 w-10">#</th>
            <th className="py-2.5 px-3 text-left font-medium text-slate-600" style={{ width: '42%' }}>Задача</th>
            <th className="py-2.5 px-3 text-left font-medium text-slate-600" style={{ width: '12%' }}>Приоритет</th>
            <th className="py-2.5 px-3 text-left font-medium text-slate-600" style={{ width: '18%' }}>Ответственный</th>
            <th className="py-2.5 pl-3 pr-6 text-left font-medium text-slate-600" style={{ width: '12%' }}>Срок</th>
          </tr>
        </thead>
        <tbody>
          {sortedTasks.map((task, idx) => {
            const category = task.category || 'Без категории';
            const showCategoryHeader = category !== currentCategory;
            currentCategory = category;
            taskNumber++;
            const priority = priorityText[task.priority || 'medium'] || priorityText.medium;

            return (
              <React.Fragment key={`task-${idx}`}>
                {showCategoryHeader && (
                  <tr className="bg-slate-50">
                    <td colSpan={5} className="py-2 pl-6 pr-6 text-xs font-semibold text-slate-700 uppercase tracking-wide border-b border-slate-200">
                      {category}
                    </td>
                  </tr>
                )}
                <tr className="border-b border-slate-100 hover:bg-blue-50/50 transition-colors">
                  <td className="py-2.5 pl-6 pr-2 text-slate-400 text-xs">
                    {taskNumber}
                  </td>
                  <td className="py-2.5 px-3 text-slate-700">
                    {task.description}
                  </td>
                  <td className={`py-2.5 px-3 text-xs font-medium ${priority.color}`}>
                    {priority.label}
                  </td>
                  <td className="py-2.5 px-3 text-slate-600">
                    {task.responsible || <span className="text-slate-300">—</span>}
                  </td>
                  <td className="py-2.5 pl-3 pr-6 text-slate-500 text-xs whitespace-nowrap">
                    {task.deadline || <span className="text-slate-300">—</span>}
                  </td>
                </tr>
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// Section type for navigation
type SectionId = 'participants' | 'summary' | 'atmosphere' | 'concerns' | 'risks' | 'tasks';

// Analytics Modal Component - Full screen with sidebar navigation
function AnalyticsModal({
  analyticsId,
  detail,
  isLoading,
  onClose,
  canSeeFullRiskBrief = true,
}: {
  analyticsId: number;
  detail?: AnalyticsDetail;
  isLoading: boolean;
  onClose: () => void;
  canSeeFullRiskBrief?: boolean;
}) {
  const [activeSection, setActiveSection] = useState<SectionId>('summary');
  const riskBrief = detail?.risk_brief_json;
  const basicReport = detail?.basic_report_json;
  const hasRiskBriefData = riskBrief && riskBrief.risks && riskBrief.risks.length > 0;
  const hasTasks = basicReport?.tasks && basicReport.tasks.length > 0;

  // Viewer sees limited data (no risks, no atmosphere, no risk_brief download)
  const showRisks = canSeeFullRiskBrief && hasRiskBriefData;
  const showAtmosphere = canSeeFullRiskBrief && riskBrief?.atmosphere;

  // Check for participants
  const hasParticipants = detail?.participants && detail.participants.length > 0;

  // Build sections list
  const sections: Array<{ id: SectionId; label: string; count?: number; show: boolean }> = [
    { id: 'participants', label: 'Участники', count: detail?.participants?.reduce((acc, g) => acc + g.persons.length, 0), show: !!hasParticipants },
    { id: 'summary', label: 'О совещании', show: !!riskBrief?.executive_summary },
    { id: 'atmosphere', label: 'Атмосфера', show: !!showAtmosphere },
    { id: 'concerns', label: 'Незакрытые вопросы', count: riskBrief?.concerns?.length, show: !!(riskBrief?.concerns && riskBrief.concerns.length > 0) },
    { id: 'risks', label: 'Риски', count: riskBrief?.risks?.length, show: !!showRisks },
    { id: 'tasks', label: 'Задачи', count: basicReport?.tasks?.length, show: !!hasTasks },
  ];

  const visibleSections = sections.filter(s => s.show);

  // Status badge - muted colors
  const getStatusBadge = (status: string) => {
    if (status === 'critical') return 'bg-red-100 text-red-800';
    if (status === 'attention') return 'bg-amber-100 text-amber-800';
    return 'bg-emerald-100 text-emerald-800';
  };

  const statusLabels: Record<string, string> = {
    critical: 'Критический',
    attention: 'Требует внимания',
    stable: 'Стабильный',
  };

  const atmosphereLabels: Record<string, string> = {
    tense: 'Напряжённая',
    working: 'Рабочее напряжение',
    calm: 'Спокойная',
    constructive: 'Конструктивная',
    positive: 'Позитивная',
    conflict: 'Конфликтная',
  };

  const atmosphereColors: Record<string, string> = {
    tense: 'text-red-600',
    conflict: 'text-red-600',
    working: 'text-amber-600',
    calm: 'text-emerald-600',
    constructive: 'text-emerald-600',
    positive: 'text-emerald-600',
  };

  const scrollToSection = (sectionId: SectionId) => {
    setActiveSection(sectionId);
    const el = document.getElementById(`section-${sectionId}`);
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 animate-in fade-in duration-200">
      <div className="h-full flex flex-col bg-slate-100">
        {/* Header */}
        <div className="px-6 py-3 border-b border-slate-200 bg-white flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-4">
            {/* Back button - prominent and easy to find */}
            <button
              onClick={onClose}
              className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 text-white hover:bg-slate-700 rounded-lg transition-colors shadow-sm"
            >
              <ChevronLeft className="w-5 h-5" />
              <span className="font-medium">Назад к календарю</span>
            </button>
            <div className="h-6 w-px bg-slate-200" />
            <h2 className="text-lg font-semibold text-slate-800">Сводка по совещанию</h2>
            {detail?.filename && (
              <span className="text-sm text-slate-500">• {detail.filename}</span>
            )}
            {riskBrief?.overall_status && (
              <span className={`px-2.5 py-0.5 rounded text-sm font-medium ${getStatusBadge(riskBrief.overall_status)}`}>
                {statusLabels[riskBrief.overall_status] || riskBrief.overall_status}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Download buttons with clear labels */}
            {detail?.has_risk_brief && canSeeFullRiskBrief && (
              <button
                onClick={() => downloadAnalyticsReport(analyticsId, 'risk_brief')}
                className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 rounded transition-colors flex items-center gap-1.5 cursor-pointer border border-slate-200"
                title="Скачать риск-бриф в формате PDF"
              >
                <Download className="w-4 h-4" />
                Риск-бриф (PDF)
              </button>
            )}
            {detail?.has_tasks && (
              <button
                onClick={() => downloadAnalyticsReport(analyticsId, 'tasks')}
                className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 rounded transition-colors flex items-center gap-1.5 cursor-pointer border border-slate-200"
                title="Скачать список задач в формате Excel"
              >
                <Download className="w-4 h-4" />
                Задачи (XLSX)
              </button>
            )}
          </div>
        </div>

        {/* Main content with sidebar */}
        <div className="flex-1 flex overflow-hidden">
          {/* Sidebar navigation */}
          {visibleSections.length > 1 && (
            <div className="w-56 bg-white border-r border-slate-200 flex-shrink-0 py-4">
              <nav className="space-y-1 px-3">
                {visibleSections.map((section) => (
                  <button
                    key={section.id}
                    onClick={() => scrollToSection(section.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center justify-between ${
                      activeSection === section.id
                        ? 'bg-slate-100 text-slate-900 font-medium'
                        : 'text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <span>{section.label}</span>
                    {section.count !== undefined && (
                      <span className="text-xs text-slate-400">{section.count}</span>
                    )}
                  </button>
                ))}
              </nav>
            </div>
          )}

          {/* Content area */}
          <div className="flex-1 overflow-y-auto p-6">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-slate-400 animate-spin" />
              </div>
            ) : (hasRiskBriefData || hasTasks || riskBrief || hasParticipants) ? (
              <div className="space-y-6">

                {/* Участники совещания */}
                {hasParticipants && (
                  <section id="section-participants" className="bg-white rounded-lg border border-slate-200 p-6">
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                      Участники совещания
                      <span className="ml-2 font-normal">
                        ({detail!.participants!.reduce((acc, g) => acc + g.persons.length, 0)})
                      </span>
                    </h3>
                    <div className="space-y-4">
                      {detail!.participants!.map((group, idx) => (
                        <div key={idx}>
                          <p className="text-sm font-medium text-slate-600 mb-1">{group.org_name}</p>
                          <div className="flex flex-wrap gap-2">
                            {group.persons.map((person, pIdx) => (
                              <span key={pIdx} className="px-2 py-1 bg-slate-100 text-slate-700 text-sm rounded">
                                {person}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* О совещании */}
                {riskBrief?.executive_summary && (
                  <section id="section-summary" className="bg-white rounded-lg border border-slate-200 p-6">
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                      О совещании
                    </h3>
                    <p className="text-slate-700 leading-relaxed text-[15px]">
                      {riskBrief.executive_summary}
                    </p>
                  </section>
                )}

                {/* Атмосфера */}
                {showAtmosphere && (
                  <section id="section-atmosphere" className="bg-white rounded-lg border border-slate-200 p-6">
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                      Атмосфера
                    </h3>
                    <div className="flex items-baseline gap-3">
                      <span className={`text-xl font-semibold ${atmosphereColors[riskBrief!.atmosphere] || 'text-slate-700'}`}>
                        {atmosphereLabels[riskBrief!.atmosphere] || riskBrief!.atmosphere}
                      </span>
                      {riskBrief!.atmosphere_comment && (
                        <span className="text-slate-500">— {riskBrief!.atmosphere_comment}</span>
                      )}
                    </div>
                  </section>
                )}

                {/* Незакрытые вопросы */}
                {riskBrief?.concerns && riskBrief.concerns.length > 0 && (
                  <section id="section-concerns" className="bg-white rounded-lg border border-slate-200 p-6">
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                      Незакрытые вопросы
                      <span className="ml-2 font-normal">({riskBrief.concerns.length})</span>
                    </h3>
                    <ul className="space-y-3">
                      {riskBrief.concerns.map((concern, idx) => (
                        <li key={concern.id || idx} className="flex items-start gap-3 pb-3 border-b border-slate-100 last:border-0 last:pb-0">
                          <span className="text-xs font-mono text-slate-400 mt-0.5 w-8 flex-shrink-0">
                            {concern.id || `Q${idx + 1}`}
                          </span>
                          <p className="text-slate-700 text-[15px]">{concern.title}</p>
                        </li>
                      ))}
                    </ul>
                  </section>
                )}

                {/* Риски */}
                {showRisks && (
                  <section id="section-risks" className="bg-white rounded-lg border border-slate-200 p-6">
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                      Риски
                      <span className="ml-2 font-normal">({riskBrief!.risks.length})</span>
                    </h3>
                    <div className="space-y-4">
                      {riskBrief!.risks.map((risk, idx) => (
                        <RiskCard key={risk.id || idx} risk={risk} />
                      ))}
                    </div>
                  </section>
                )}

                {/* Задачи */}
                {hasTasks && (
                  <section id="section-tasks" className="bg-white rounded-lg border border-slate-200 p-6">
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                      Задачи
                      <span className="ml-2 font-normal">({basicReport!.tasks!.length})</span>
                    </h3>
                    <TasksTable tasks={basicReport!.tasks!} />
                  </section>
                )}
              </div>
            ) : (
              // Fallback
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-slate-200 rounded-full flex items-center justify-center mx-auto mb-4">
                  <FileText className="w-8 h-8 text-slate-400" />
                </div>
                <h3 className="text-lg font-medium text-slate-700 mb-2">
                  Сводка недоступна
                </h3>
                <p className="text-slate-500 mb-6 max-w-md mx-auto">
                  {detail?.has_risk_brief
                    ? 'Скачайте PDF для просмотра.'
                    : 'Аналитика не была сгенерирована.'}
                </p>
                {detail?.has_risk_brief && (
                  <button
                    onClick={() => downloadAnalyticsReport(analyticsId, 'risk_brief')}
                    className="px-5 py-2.5 bg-slate-800 text-white rounded-lg hover:bg-slate-900 transition-colors flex items-center gap-2 font-medium mx-auto cursor-pointer"
                  >
                    <Download className="w-4 h-4" />
                    Скачать PDF
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
