import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import ruLocale from '@fullcalendar/core/locales/ru';
import {
  FileText,
  Loader2,
  ExternalLink,
  Calendar,
  User,
  Users,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { getJobs, type JobListItem } from '../../api/client';
import { STATUS_COLORS, ACCENT_COLOR_MAP, type DomainConfig } from './constants';
import { JobRow } from './JobRow';
import { StandardDetailModal } from './StandardDetailModal';

const GRID_COLS_MAP: Record<number, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-2',
  3: 'grid-cols-3',
  4: 'grid-cols-4',
  5: 'grid-cols-5',
};

export function DomainDashboard({
  domainId,
  title,
  headerIcon: HeaderIcon,
  accentColor,
  meetingTypes,
  meetingGridCols = 4,
  calendarEventTitle = 'dynamic',
  DetailModal,
}: DomainConfig) {
  const [calendarScope, setCalendarScope] = useState<'my' | 'domain'>('my');
  const [selectedJob, setSelectedJob] = useState<JobListItem | null>(null);
  const colors = ACCENT_COLOR_MAP[accentColor];

  const { data: myJobsData, isLoading: myLoading, error: myError } = useQuery({
    queryKey: [`${domainId}-jobs`, 'my'],
    queryFn: () => getJobs(100, domainId, 'my'),
  });

  const { data: domainJobsData, isLoading: domainLoading, error: domainError } = useQuery({
    queryKey: [`${domainId}-jobs`, 'domain'],
    queryFn: () => getJobs(100, domainId, 'domain'),
  });

  const jobsData = calendarScope === 'domain' ? domainJobsData : myJobsData;
  const isLoading = calendarScope === 'domain' ? domainLoading : myLoading;
  const error = calendarScope === 'domain' ? domainError : myError;

  const calendarEvents = useMemo(() => {
    if (!jobsData?.jobs) return [];
    return jobsData.jobs.map((job) => ({
      id: job.job_id,
      title: calendarEventTitle === 'dynamic' ? job.source_file : calendarEventTitle,
      date: job.created_at.split('T')[0],
      backgroundColor: STATUS_COLORS[job.status] || '#6c757d',
      borderColor: 'transparent',
      extendedProps: { job_id: job.job_id, status: job.status },
    }));
  }, [jobsData, calendarEventTitle]);

  const recentJobs = useMemo(() => {
    if (!jobsData?.jobs) return [];
    return jobsData.jobs
      .filter(j => j.status === 'completed')
      .slice(0, 10);
  }, [jobsData]);

  const findJob = (jobId: string): JobListItem | undefined => {
    return myJobsData?.jobs.find(j => j.job_id === jobId)
      || domainJobsData?.jobs.find(j => j.job_id === jobId);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[600px]">
        <Loader2 className={`w-10 h-10 ${colors.spinnerText} animate-spin`} />
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

  const ModalComponent = DetailModal;

  return (
    <div className="bg-slate-50 min-h-full">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className={`bg-gradient-to-r ${colors.gradientFrom} ${colors.gradientTo} rounded-xl p-6 text-white`}>
          <div className="flex items-center gap-3 mb-2">
            <HeaderIcon className="w-8 h-8" />
            <h1 className="text-2xl font-bold">{title}</h1>
          </div>
        </div>

        {/* Scope Tabs + Calendar */}
        <div className="bg-white rounded-xl border border-slate-200 p-4" data-tour="dashboard-calendar">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-slate-800 flex items-center gap-2">
              <Calendar className={`w-5 h-5 ${colors.calendarIcon}`} />
              Календарь
            </h3>
            <div className="flex bg-slate-100 rounded-lg p-0.5" data-tour="dashboard-scope">
              <button
                onClick={() => setCalendarScope('my')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  calendarScope === 'my'
                    ? `${colors.activeBg} text-white shadow-sm`
                    : 'text-slate-600 hover:text-slate-800'
                }`}
              >
                <User className="w-3.5 h-3.5" />
                Мои записи
              </button>
              <button
                onClick={() => setCalendarScope('domain')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  calendarScope === 'domain'
                    ? `${colors.activeBg} text-white shadow-sm`
                    : 'text-slate-600 hover:text-slate-800'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                Департамент
              </button>
            </div>
          </div>
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
              const jobId = info.event.extendedProps.job_id || info.event.id;
              if (jobId) {
                const job = findJob(jobId);
                if (job) setSelectedJob(job);
              }
            }}
            height="auto"
            contentHeight={450}
          />
        </div>

        {/* Meeting Types */}
        <div className="bg-white rounded-xl border border-slate-200 p-6" data-tour="dashboard-meeting-types">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Типы встреч</h2>
          <div className={`grid ${GRID_COLS_MAP[meetingGridCols] || 'grid-cols-4'} gap-4`}>
            {meetingTypes.map((type) => {
              const Icon = type.icon;
              return (
                <Link
                  key={type.id}
                  to="/"
                  className={`p-4 border border-slate-200 rounded-lg ${type.hoverBorder} ${type.hoverBg} transition-all text-center`}
                >
                  <div className={`w-10 h-10 rounded-lg ${type.color} flex items-center justify-center mx-auto mb-3`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <p className="font-medium text-slate-800 text-sm">{type.name}</p>
                </Link>
              );
            })}
          </div>
        </div>

        {/* Recent Transcriptions */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden" data-tour="dashboard-recent">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-800">Последние записи</h2>
            <Link
              to="/history"
              className={`text-sm ${colors.linkText} ${colors.linkHover} flex items-center gap-1`}
            >
              Все записи <ExternalLink className="w-4 h-4" />
            </Link>
          </div>

          {recentJobs.length > 0 ? (
            <div className="divide-y divide-slate-100">
              {recentJobs.map((job) => (
                <JobRow key={job.job_id} job={job} accentColor={accentColor} onClick={() => setSelectedJob(job)} />
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-slate-500">
              <FileText className="w-12 h-12 mx-auto mb-3 text-slate-300" />
              <p>Нет завершённых записей</p>
            </div>
          )}
        </div>
      </div>

      {/* Detail Modal */}
      {selectedJob && (
        ModalComponent
          ? <ModalComponent job={selectedJob} onClose={() => setSelectedJob(null)} />
          : <StandardDetailModal job={selectedJob} onClose={() => setSelectedJob(null)} accentColor={accentColor} />
      )}
    </div>
  );
}
