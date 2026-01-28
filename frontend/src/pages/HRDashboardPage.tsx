/**
 * HR Domain Dashboard
 *
 * Dashboard for HR domain - shows meeting statistics and transcription history.
 * HR domain doesn't have projects, just meeting types (recruitment, 1on1, etc.)
 */
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Users,
  FileText,
  Clock,
  TrendingUp,
  UserPlus,
  UserCheck,
  Briefcase,
  GraduationCap,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { getJobs, type JobListItem } from '../api/client';

// HR Meeting types with icons and colors
const HR_MEETING_TYPES = [
  { id: 'recruitment', name: 'Собеседования', icon: UserPlus, color: 'bg-blue-100 text-blue-600' },
  { id: 'one_on_one', name: 'Встречи 1-на-1', icon: Users, color: 'bg-purple-100 text-purple-600' },
  { id: 'performance_review', name: 'Performance Review', icon: TrendingUp, color: 'bg-green-100 text-green-600' },
  { id: 'team_meeting', name: 'Командные встречи', icon: Briefcase, color: 'bg-amber-100 text-amber-600' },
  { id: 'onboarding', name: 'Onboarding', icon: GraduationCap, color: 'bg-pink-100 text-pink-600' },
];

export function HRDashboardPage() {
  // Fetch recent jobs filtered by HR domain
  const { data: jobsData, isLoading, error } = useQuery({
    queryKey: ['hr-jobs'],
    queryFn: () => getJobs(100, 'hr'),
  });

  // Compute statistics from real data
  const stats = useMemo(() => {
    if (!jobsData?.jobs) return null;

    const total = jobsData.jobs.length;
    const completed = jobsData.jobs.filter(j => j.status === 'completed').length;
    const processing = jobsData.jobs.filter(j => j.status === 'processing').length;
    const pending = jobsData.jobs.filter(j => j.status === 'pending').length;

    // TODO: Count by meeting type from actual job data when backend supports it
    const byType: Record<string, number> = {};
    HR_MEETING_TYPES.forEach(type => {
      byType[type.id] = 0;
    });

    return { total, completed, processing, pending, byType };
  }, [jobsData]);

  // Recent completed jobs
  const recentJobs = useMemo(() => {
    if (!jobsData?.jobs) return [];
    return jobsData.jobs
      .filter(j => j.status === 'completed')
      .slice(0, 10);
  }, [jobsData]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-10 h-10 text-purple-500 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
          <h2 className="font-semibold mb-2">Ошибка загрузки</h2>
          <p className="text-sm">Не удалось загрузить данные дашборда.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-purple-700 rounded-xl p-6 text-white">
        <div className="flex items-center gap-3 mb-2">
          <Users className="w-8 h-8" />
          <h1 className="text-2xl font-bold">HR Dashboard</h1>
        </div>
        <p className="text-purple-100">
          Аналитика и статистика по HR встречам
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4">
        <KPICard
          label="Всего встреч"
          value={stats?.total || 0}
          icon={FileText}
          color="slate"
        />
        <KPICard
          label="Обработано"
          value={stats?.completed || 0}
          icon={UserCheck}
          color="green"
        />
        <KPICard
          label="В обработке"
          value={stats?.processing || 0}
          icon={Clock}
          color="amber"
        />
        <KPICard
          label="В очереди"
          value={stats?.pending || 0}
          icon={Clock}
          color="slate"
        />
      </div>

      {/* Meeting Types Grid */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">Типы встреч</h2>
        <div className="grid grid-cols-5 gap-4">
          {HR_MEETING_TYPES.map((type) => {
            const Icon = type.icon;
            const count = stats?.byType[type.id] || 0;

            return (
              <div
                key={type.id}
                className="p-4 border border-slate-200 rounded-lg hover:border-purple-300 transition-colors"
              >
                <div className={`w-10 h-10 rounded-lg ${type.color} flex items-center justify-center mb-3`}>
                  <Icon className="w-5 h-5" />
                </div>
                <p className="text-2xl font-bold text-slate-800">{count}</p>
                <p className="text-sm text-slate-500">{type.name}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Transcriptions */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800">Последние транскрипции</h2>
          <Link
            to="/history"
            className="text-sm text-purple-600 hover:text-purple-700 flex items-center gap-1"
          >
            Все записи <ExternalLink className="w-4 h-4" />
          </Link>
        </div>

        {recentJobs.length > 0 ? (
          <div className="divide-y divide-slate-100">
            {recentJobs.map((job) => (
              <JobRow key={job.job_id} job={job} />
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500">
            <FileText className="w-12 h-12 mx-auto mb-3 text-slate-300" />
            <p>Нет завершённых транскрипций</p>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">Быстрые действия</h2>
        <div className="grid grid-cols-3 gap-4">
          <Link
            to="/"
            className="p-4 border border-slate-200 rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-all text-center"
          >
            <UserPlus className="w-8 h-8 mx-auto mb-2 text-purple-600" />
            <p className="font-medium text-slate-800">Загрузить собеседование</p>
            <p className="text-sm text-slate-500">Recruitment</p>
          </Link>

          <Link
            to="/"
            className="p-4 border border-slate-200 rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-all text-center"
          >
            <Users className="w-8 h-8 mx-auto mb-2 text-purple-600" />
            <p className="font-medium text-slate-800">Загрузить 1-на-1</p>
            <p className="text-sm text-slate-500">One on One</p>
          </Link>

          <Link
            to="/"
            className="p-4 border border-slate-200 rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-all text-center"
          >
            <TrendingUp className="w-8 h-8 mx-auto mb-2 text-purple-600" />
            <p className="font-medium text-slate-800">Performance Review</p>
            <p className="text-sm text-slate-500">Оценка сотрудника</p>
          </Link>
        </div>
      </div>
    </div>
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
  color: 'slate' | 'green' | 'amber' | 'purple';
}) {
  const colorClasses = {
    slate: 'bg-slate-100 text-slate-600',
    green: 'bg-green-100 text-green-600',
    amber: 'bg-amber-100 text-amber-600',
    purple: 'bg-purple-100 text-purple-600',
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

// Job Row Component
function JobRow({ job }: { job: JobListItem }) {
  return (
    <Link
      to={`/job/${job.job_id}`}
      className="p-4 flex items-center gap-4 hover:bg-slate-50 transition-colors"
    >
      <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
        <FileText className="w-5 h-5 text-purple-600" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-slate-800 truncate">{job.source_file}</p>
        <p className="text-sm text-slate-500">
          {new Date(job.created_at).toLocaleString('ru-RU')}
        </p>
      </div>
      <div className="text-sm text-green-600 font-medium">
        Готово
      </div>
    </Link>
  );
}

export default HRDashboardPage;
