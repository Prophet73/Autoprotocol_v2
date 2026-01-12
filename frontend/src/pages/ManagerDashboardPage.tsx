import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LayoutDashboard,
  FileText,
  Clock,
  Users,
  CheckCircle,
  XCircle,
  Loader2,
  ChevronRight,
  Calendar
} from 'lucide-react';
import { getMyProjects, getProjectDashboard } from '../api/client';
import type { ProjectSummary } from '../api/client';

export function ManagerDashboardPage() {
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);

  // Fetch manager's projects
  const { data: projects, isLoading: projectsLoading, error: projectsError } = useQuery({
    queryKey: ['my-projects'],
    queryFn: getMyProjects,
  });

  // Fetch dashboard data for selected project
  const { data: dashboardData, isLoading: dashboardLoading } = useQuery({
    queryKey: ['project-dashboard', selectedProjectId],
    queryFn: () => getProjectDashboard(selectedProjectId!),
    enabled: !!selectedProjectId,
  });

  if (projectsLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 text-[#E52713] animate-spin" />
      </div>
    );
  }

  if (projectsError) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
          <h2 className="font-semibold mb-2">Ошибка загрузки проектов</h2>
          <p className="text-sm">Не удалось загрузить список ваших проектов. Попробуйте обновить страницу.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <LayoutDashboard className="w-7 h-7 text-[#E52713]" />
          Мои проекты
        </h1>
        <p className="text-slate-500 mt-1">
          Выберите проект для просмотра статистики и отчётов
        </p>
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {projects?.map((project) => (
          <ProjectCard
            key={project.id}
            project={project}
            isSelected={selectedProjectId === project.id}
            onClick={() => setSelectedProjectId(project.id)}
          />
        ))}
        {projects?.length === 0 && (
          <div className="col-span-full text-center py-12 text-slate-500">
            <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>У вас пока нет назначенных проектов</p>
          </div>
        )}
      </div>

      {/* Dashboard for selected project */}
      {selectedProjectId && (
        <div className="space-y-6">
          {dashboardLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-[#E52713] animate-spin" />
            </div>
          ) : dashboardData ? (
            <>
              {/* Stats Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <StatCard
                  label="Всего отчётов"
                  value={dashboardData.total_reports}
                  icon={FileText}
                  color="red"
                />
                <StatCard
                  label="Проектов"
                  value={Object.keys(dashboardData.by_project).length}
                  icon={LayoutDashboard}
                  color="blue"
                />
                <StatCard
                  label="Участников"
                  value={Object.keys(dashboardData.speaker_stats).length}
                  icon={Users}
                  color="purple"
                />
                <StatCard
                  label="Последние 30 дней"
                  value={dashboardData.timeline.filter(r => {
                    if (!r.created_at) return false;
                    const date = new Date(r.created_at);
                    const thirtyDaysAgo = new Date();
                    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
                    return date >= thirtyDaysAgo;
                  }).length}
                  icon={Calendar}
                  color="amber"
                />
              </div>

              {/* Timeline */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="p-4 border-b border-slate-100">
                  <h3 className="font-semibold text-slate-800">Последние отчёты</h3>
                </div>
                <div className="divide-y divide-slate-100">
                  {dashboardData.timeline.slice(0, 10).map((item) => (
                    <div key={item.id} className="p-4 flex items-center gap-4 hover:bg-slate-50">
                      <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center">
                        <FileText className="w-5 h-5 text-[#E52713]" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-slate-800 truncate">{item.title}</p>
                        <p className="text-sm text-slate-500">
                          {item.created_at ? new Date(item.created_at).toLocaleDateString('ru-RU', {
                            day: 'numeric',
                            month: 'long',
                            year: 'numeric'
                          }) : 'Дата не указана'}
                        </p>
                      </div>
                      <ChevronRight className="w-5 h-5 text-slate-400" />
                    </div>
                  ))}
                  {dashboardData.timeline.length === 0 && (
                    <div className="p-8 text-center text-slate-500">
                      Нет отчётов для отображения
                    </div>
                  )}
                </div>
              </div>

              {/* Speaker Stats */}
              {Object.keys(dashboardData.speaker_stats).length > 0 && (
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                  <div className="p-4 border-b border-slate-100">
                    <h3 className="font-semibold text-slate-800">Статистика участников</h3>
                  </div>
                  <div className="p-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {Object.entries(dashboardData.speaker_stats).slice(0, 6).map(([speakerId, stats]) => (
                        <div key={speakerId} className="p-4 bg-slate-50 rounded-lg">
                          <div className="flex items-center gap-3 mb-2">
                            <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
                              <Users className="w-4 h-4 text-[#E52713]" />
                            </div>
                            <span className="font-medium text-slate-800">{speakerId}</span>
                          </div>
                          <div className="text-sm text-slate-500 space-y-1">
                            <p>Выступлений: {stats.appearances}</p>
                            <p>Время: {Math.round(stats.total_time / 60)} мин</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}

// Project Card Component
function ProjectCard({
  project,
  isSelected,
  onClick
}: {
  project: ProjectSummary;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`text-left p-4 rounded-xl border-2 transition-all ${
        isSelected
          ? 'border-[#E52713] bg-red-50 shadow-lg shadow-red-500/10'
          : 'border-slate-200 bg-white hover:border-[#E52713]/50 hover:shadow-md'
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-slate-800">{project.name}</h3>
          <p className="text-sm text-slate-500">Код: {project.project_code}</p>
        </div>
        <span className={`px-2 py-1 text-xs rounded-full ${
          project.is_active
            ? 'bg-red-100 text-[#E52713]'
            : 'bg-slate-100 text-slate-600'
        }`}>
          {project.is_active ? 'Активен' : 'Архив'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="flex items-center gap-1 text-slate-600">
          <FileText className="w-4 h-4" />
          <span>{project.total_reports} отчётов</span>
        </div>
        <div className="flex items-center gap-1 text-[#E52713]">
          <CheckCircle className="w-4 h-4" />
          <span>{project.completed_reports} готово</span>
        </div>
        <div className="flex items-center gap-1 text-amber-600">
          <Clock className="w-4 h-4" />
          <span>{project.pending_reports} в работе</span>
        </div>
        <div className="flex items-center gap-1 text-red-600">
          <XCircle className="w-4 h-4" />
          <span>{project.failed_reports} ошибок</span>
        </div>
      </div>

      {project.last_report_date && (
        <p className="mt-3 text-xs text-slate-400">
          Последний отчёт: {new Date(project.last_report_date).toLocaleDateString('ru-RU')}
        </p>
      )}
    </button>
  );
}

// Stat Card Component
function StatCard({
  label,
  value,
  icon: Icon,
  color
}: {
  label: string;
  value: number;
  icon: React.ElementType;
  color: 'red' | 'blue' | 'purple' | 'amber';
}) {
  const colorClasses = {
    red: 'bg-red-100 text-[#E52713]',
    blue: 'bg-blue-100 text-blue-600',
    purple: 'bg-purple-100 text-purple-600',
    amber: 'bg-amber-100 text-amber-600',
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
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
