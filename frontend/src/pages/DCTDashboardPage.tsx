/**
 * DCT Domain Dashboard - Департамент Цифровой Трансформации
 *
 * Dashboard for DCT domain - shows meeting statistics and transcription history.
 * Meeting types: brainstorm, production, negotiation, lecture
 */
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Monitor,
  FileText,
  Clock,
  Lightbulb,
  Factory,
  Handshake,
  GraduationCap,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { getJobs, type JobListItem } from '../api/client';

// DCT Meeting types with icons and colors
const DCT_MEETING_TYPES = [
  { id: 'brainstorm', name: 'Мозговой штурм', icon: Lightbulb, color: 'bg-yellow-100 text-yellow-600' },
  { id: 'production', name: 'Производственное совещание', icon: Factory, color: 'bg-blue-100 text-blue-600' },
  { id: 'negotiation', name: 'Переговоры с контрагентом', icon: Handshake, color: 'bg-green-100 text-green-600' },
  { id: 'lecture', name: 'Лекция/Вебинар', icon: GraduationCap, color: 'bg-purple-100 text-purple-600' },
];

export function DCTDashboardPage() {
  // Fetch recent jobs filtered by DCT domain
  const { data: jobsData, isLoading, error } = useQuery({
    queryKey: ['dct-jobs'],
    queryFn: () => getJobs(100, 'dct'),
  });

  // Compute statistics from real data
  const stats = useMemo(() => {
    if (!jobsData?.jobs) return null;

    const total = jobsData.jobs.length;
    const completed = jobsData.jobs.filter(j => j.status === 'completed').length;
    const processing = jobsData.jobs.filter(j => j.status === 'processing').length;
    const pending = jobsData.jobs.filter(j => j.status === 'pending').length;

    // Count by meeting type from actual job data
    const byType: Record<string, number> = {};
    DCT_MEETING_TYPES.forEach(type => {
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
        <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
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
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white">
        <div className="flex items-center gap-3 mb-2">
          <Monitor className="w-8 h-8" />
          <h1 className="text-2xl font-bold">Департамент Цифровой Трансформации</h1>
        </div>
        <p className="text-blue-100">
          Аналитика и статистика по встречам ДЦТ
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
          icon={Monitor}
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
        <div className="grid grid-cols-4 gap-4">
          {DCT_MEETING_TYPES.map((type) => {
            const Icon = type.icon;
            const count = stats?.byType[type.id] || 0;

            return (
              <div
                key={type.id}
                className="p-4 border border-slate-200 rounded-lg hover:border-blue-300 transition-colors"
              >
                <div className={`w-10 h-10 rounded-lg ${type.color} flex items-center justify-center mb-3`}>
                  <Icon className="w-5 h-5" />
                </div>
                <p className="text-2xl font-bold text-slate-800">{count}</p>
                <p className="text-xs text-slate-500">{type.name}</p>
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
            className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
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
        <div className="grid grid-cols-4 gap-4">
          <Link
            to="/"
            className="p-4 border border-slate-200 rounded-lg hover:border-yellow-300 hover:bg-yellow-50 transition-all text-center"
          >
            <Lightbulb className="w-8 h-8 mx-auto mb-2 text-yellow-600" />
            <p className="font-medium text-slate-800">Мозговой штурм</p>
            <p className="text-xs text-slate-500">Загрузить brainstorm</p>
          </Link>

          <Link
            to="/"
            className="p-4 border border-slate-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-all text-center"
          >
            <Factory className="w-8 h-8 mx-auto mb-2 text-blue-600" />
            <p className="font-medium text-slate-800">Производственное</p>
            <p className="text-xs text-slate-500">Совещание</p>
          </Link>

          <Link
            to="/"
            className="p-4 border border-slate-200 rounded-lg hover:border-green-300 hover:bg-green-50 transition-all text-center"
          >
            <Handshake className="w-8 h-8 mx-auto mb-2 text-green-600" />
            <p className="font-medium text-slate-800">Переговоры</p>
            <p className="text-xs text-slate-500">С контрагентом</p>
          </Link>

          <Link
            to="/"
            className="p-4 border border-slate-200 rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-all text-center"
          >
            <GraduationCap className="w-8 h-8 mx-auto mb-2 text-purple-600" />
            <p className="font-medium text-slate-800">Лекция/Вебинар</p>
            <p className="text-xs text-slate-500">Конспект</p>
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
  color: 'slate' | 'green' | 'amber' | 'blue';
}) {
  const colorClasses = {
    slate: 'bg-slate-100 text-slate-600',
    green: 'bg-green-100 text-green-600',
    amber: 'bg-amber-100 text-amber-600',
    blue: 'bg-blue-100 text-blue-600',
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
      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
        <FileText className="w-5 h-5 text-blue-600" />
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

export default DCTDashboardPage;
