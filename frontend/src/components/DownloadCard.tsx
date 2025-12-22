import { Download, FileText, FileSpreadsheet, Brain, FileCode } from 'lucide-react';
import { getDownloadUrl } from '../api/client';

interface DownloadCardProps {
  jobId: string;
  outputFiles: Record<string, string>;
}

const fileConfig: Record<string, { label: string; icon: typeof FileText; color: string; desc: string }> = {
  transcript: {
    label: 'Транскрибация',
    icon: FileText,
    color: 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100',
    desc: 'Полный текст с таймкодами',
  },
  tasks: {
    label: 'Excel отчёт',
    icon: FileSpreadsheet,
    color: 'border-green-200 bg-green-50 text-green-700 hover:bg-green-100',
    desc: 'Задачи и поручения',
  },
  report: {
    label: 'Word отчёт',
    icon: FileText,
    color: 'border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100',
    desc: 'Протокол совещания',
  },
  analysis: {
    label: 'ИИ Анализ',
    icon: Brain,
    color: 'border-purple-200 bg-purple-50 text-purple-700 hover:bg-purple-100',
    desc: 'Глубокий анализ',
  },
  protocol_docx: {
    label: 'Протокол (Word)',
    icon: FileText,
    color: 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100',
    desc: 'Готовый протокол',
  },
  protocol_txt: {
    label: 'Протокол (текст)',
    icon: FileText,
    color: 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100',
    desc: 'Текстовая версия',
  },
  result_json: {
    label: 'JSON данные',
    icon: FileCode,
    color: 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100',
    desc: 'Структурированные данные',
  },
};

export function DownloadCard({ jobId, outputFiles }: DownloadCardProps) {
  const files = Object.entries(outputFiles);

  if (files.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        Нет файлов для скачивания
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {files.map(([fileType, filePath]) => {
        const config = fileConfig[fileType] || {
          label: fileType,
          icon: FileText,
          color: 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100',
          desc: 'Файл',
        };
        const Icon = config.icon;
        const fileName = filePath.split(/[\\/]/).pop() || filePath;

        return (
          <a
            key={fileType}
            href={getDownloadUrl(jobId, fileType)}
            download
            className={`flex items-center gap-4 p-4 rounded-xl border-2 transition-all ${config.color}`}
          >
            <div className="p-2 bg-white rounded-lg shadow-sm">
              <Icon className="w-6 h-6" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold">{config.label}</p>
              <p className="text-sm opacity-70 truncate">{config.desc}</p>
            </div>
            <Download className="w-5 h-5 opacity-50" />
          </a>
        );
      })}
    </div>
  );
}
