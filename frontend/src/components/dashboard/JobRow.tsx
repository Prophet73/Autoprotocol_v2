import { FileText } from 'lucide-react';
import type { JobListItem } from '../../api/client';
import { STATUS_LABELS, ACCENT_COLOR_MAP, type AccentColor } from './constants';

interface JobRowProps {
  job: JobListItem;
  accentColor: AccentColor;
  onClick: () => void;
}

export function JobRow({ job, accentColor, onClick }: JobRowProps) {
  const colors = ACCENT_COLOR_MAP[accentColor];

  return (
    <button
      onClick={onClick}
      className="w-full p-4 flex items-center gap-4 hover:bg-slate-50 transition-colors text-left"
    >
      <div className={`w-10 h-10 ${colors.iconBg} rounded-lg flex items-center justify-center`}>
        <FileText className={`w-5 h-5 ${colors.iconText}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-slate-800 truncate">{job.source_file}</p>
        <p className="text-sm text-slate-500">
          {new Date(job.created_at).toLocaleString('ru-RU')}
        </p>
      </div>
      <div className="text-sm font-medium">
        <span className={`px-2 py-1 rounded text-xs ${
          job.status === 'completed' ? 'bg-green-100 text-green-700' :
          job.status === 'processing' ? 'bg-amber-100 text-amber-700' :
          job.status === 'failed' ? 'bg-red-100 text-red-700' :
          'bg-slate-100 text-slate-600'
        }`}>
          {STATUS_LABELS[job.status] || job.status}
        </span>
      </div>
    </button>
  );
}
