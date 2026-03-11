import { useState, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import ruLocale from '@fullcalendar/core/locales/ru';
import {
  FileText,
  AlertTriangle,
  Flame,
  Loader2,
  Calendar,
} from 'lucide-react';
import {
  getManagerDashboardView,
  getAnalyticsDetail,
  updateProblemStatus,
} from '../api/client';
import {
  ProjectsSidebar,
  KPICard,
  AttentionItemRow,
  PulseChart,
  AnalyticsModal,
} from '../components/manager';

export function ManagerDashboardPage() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [projectSearch, setProjectSearch] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedAnalyticsId, setSelectedAnalyticsId] = useState<number | null>(null);

  // Handle deep link: ?analytics=ID opens the analytics modal automatically
  useEffect(() => {
    const analyticsParam = searchParams.get('analytics');
    if (analyticsParam) {
      const analyticsId = parseInt(analyticsParam, 10);
      if (!isNaN(analyticsId) && analyticsId > 0) {
        setSelectedAnalyticsId(analyticsId);
        // Clear the URL param after opening modal (clean URL)
        setSearchParams({}, { replace: true });
      }
    }
  }, [searchParams, setSearchParams]);

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
        <ProjectsSidebar
          projects={filteredProjects}
          selectedProjectId={selectedProjectId}
          onSelectProject={setSelectedProjectId}
          projectSearch={projectSearch}
          onSearchChange={setProjectSearch}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />

        {/* Center Column - Main Content */}
        <div className="bg-slate-50 overflow-y-auto">
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
            <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6" data-tour="dashboard-calendar">
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
              <PulseChart pulseChartData={pulseChartData} />
            )
          )}

          {/* Attention Items / Triage */}
          {sortedAttentionItems.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden" data-tour="dashboard-recent">
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
