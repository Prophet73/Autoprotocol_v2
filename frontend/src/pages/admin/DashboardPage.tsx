import { useEffect, useState } from 'react';
import { statsApi } from '../../api/adminApi';
import type { GlobalStats, SystemHealth } from '../../api/adminApi';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color: string;
}

function StatCard({ title, value, subtitle, icon, color }: StatCardProps) {
  return (
    <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-slate-500 text-sm">{title}</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">{value}</p>
          {subtitle && <p className="text-slate-400 text-xs mt-1">{subtitle}</p>}
        </div>
        <div className={`w-12 h-12 ${color} rounded-lg flex items-center justify-center`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

function HealthIndicator({ label, healthy }: { label: string; healthy: boolean }) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-slate-600">{label}</span>
      <span className={`px-2 py-1 rounded text-xs font-medium ${
        healthy ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
      }`}>
        {healthy ? 'OK' : 'Ошибка'}
      </span>
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<GlobalStats | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsData, healthData] = await Promise.all([
        statsApi.getGlobal(),
        statsApi.getHealth(),
      ]);
      setStats(statsData);
      setHealth(healthData);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">{error}</p>
        <button
          onClick={loadData}
          className="mt-2 text-sm text-red-500 hover:text-red-700 underline"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Дашборд</h1>
          <p className="text-slate-500 mt-1">Обзор системы</p>
        </div>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition flex items-center border border-slate-200"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Обновить
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Всего пользователей"
          value={stats?.users.total_users || 0}
          subtitle={`Активных: ${stats?.users.active_users || 0}`}
          color="bg-blue-600"
          icon={
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          }
        />

        <StatCard
          title="Транскрипций"
          value={stats?.transcriptions.total || 0}
          subtitle={`В обработке: ${stats?.transcriptions.processing || 0}`}
          color="bg-green-600"
          icon={
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          }
        />

        <StatCard
          title="Хранилище"
          value={`${stats?.storage.total_gb?.toFixed(2) || 0} GB`}
          subtitle={`Загрузки: ${((stats?.storage.uploads_bytes || 0) / 1024 / 1024 / 1024).toFixed(2)} GB`}
          color="bg-purple-600"
          icon={
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
            </svg>
          }
        />

        <StatCard
          title="Ошибок"
          value={stats?.transcriptions.failed || 0}
          subtitle={`Ожидают: ${stats?.transcriptions.pending || 0}`}
          color="bg-red-600"
          icon={
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          }
        />
      </div>

      {/* Second row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* System Health */}
        <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Состояние системы</h3>
          <div className="space-y-1 divide-y divide-slate-200">
            <HealthIndicator label="База данных" healthy={health?.database || false} />
            <HealthIndicator label="Redis" healthy={health?.redis || false} />
            <HealthIndicator label="GPU" healthy={health?.gpu || false} />
            <HealthIndicator label="Celery" healthy={health?.celery || false} />
          </div>
          <div className="mt-4 pt-4 border-t border-slate-200">
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">Диск</span>
              <span className="text-slate-800">{health?.disk_usage_percent?.toFixed(1) || 0}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2 mt-2">
              <div
                className={`h-2 rounded-full ${
                  (health?.disk_usage_percent || 0) > 90 ? 'bg-red-500' :
                  (health?.disk_usage_percent || 0) > 70 ? 'bg-yellow-500' : 'bg-green-500'
                }`}
                style={{ width: `${health?.disk_usage_percent || 0}%` }}
              />
            </div>
            <div className="flex justify-between text-sm mt-4">
              <span className="text-slate-500">Память</span>
              <span className="text-slate-800">{health?.memory_usage_percent?.toFixed(1) || 0}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2 mt-2">
              <div
                className={`h-2 rounded-full ${
                  (health?.memory_usage_percent || 0) > 90 ? 'bg-red-500' :
                  (health?.memory_usage_percent || 0) > 70 ? 'bg-yellow-500' : 'bg-green-500'
                }`}
                style={{ width: `${health?.memory_usage_percent || 0}%` }}
              />
            </div>
          </div>
        </div>

        {/* Transcription Stats */}
        <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Статус транскрипций</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <span className="w-3 h-3 bg-yellow-500 rounded-full mr-2"></span>
                <span className="text-slate-600">Ожидают</span>
              </div>
              <span className="text-slate-800 font-medium">{stats?.transcriptions.pending || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <span className="w-3 h-3 bg-blue-500 rounded-full mr-2"></span>
                <span className="text-slate-600">В обработке</span>
              </div>
              <span className="text-slate-800 font-medium">{stats?.transcriptions.processing || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <span className="w-3 h-3 bg-green-500 rounded-full mr-2"></span>
                <span className="text-slate-600">Завершено</span>
              </div>
              <span className="text-slate-800 font-medium">{stats?.transcriptions.completed || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <span className="w-3 h-3 bg-red-500 rounded-full mr-2"></span>
                <span className="text-slate-600">Ошибка</span>
              </div>
              <span className="text-slate-800 font-medium">{stats?.transcriptions.failed || 0}</span>
            </div>
          </div>
        </div>

        {/* Users by Role */}
        <div className="bg-white rounded-lg p-6 shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Пользователи по ролям</h3>
          <div className="space-y-3">
            {stats?.users.by_role && Object.entries(stats.users.by_role).length > 0 ? (
              Object.entries(stats.users.by_role).map(([role, count]) => (
                <div key={role} className="flex items-center justify-between">
                  <span className="text-slate-600 capitalize">{role}</span>
                  <span className="text-slate-800 font-medium">{count}</span>
                </div>
              ))
            ) : (
              <p className="text-slate-400 text-sm">Нет данных</p>
            )}
          </div>

          <h4 className="text-sm font-medium text-slate-500 mt-6 mb-3">По доменам</h4>
          <div className="space-y-3">
            {stats?.users.by_domain && Object.entries(stats.users.by_domain).length > 0 ? (
              Object.entries(stats.users.by_domain).map(([domain, count]) => (
                <div key={domain} className="flex items-center justify-between">
                  <span className="text-slate-600">{domain || 'Без домена'}</span>
                  <span className="text-slate-800 font-medium">{count}</span>
                </div>
              ))
            ) : (
              <p className="text-slate-400 text-sm">Нет данных</p>
            )}
          </div>
        </div>
      </div>

      {/* Footer info */}
      <div className="text-center text-slate-500 text-sm">
        <p>
          Данные обновлены: {stats?.generated_at ? new Date(stats.generated_at).toLocaleString('ru-RU') : 'N/A'}
        </p>
        <p className="mt-1">
          GPU: {stats?.gpu_available ? 'Доступен' : 'Недоступен'} |
          Redis: {stats?.redis_connected ? 'Подключен' : 'Отключен'}
        </p>
      </div>
    </div>
  );
}
