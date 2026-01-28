import { useState } from 'react';
import { Download, FileText, FileSpreadsheet, Brain, FileCode, Archive, Shield, Loader2 } from 'lucide-react';
import { downloadJobFile, downloadJobFileAll } from '../api/client';

interface DownloadCardProps {
  jobId: string;
  outputFiles: Record<string, string>;
}

const fileConfig: Record<string, { label: string; icon: typeof FileText; color: string; desc: string }> = {
  transcript: {
    label: 'Транскрибация',
    icon: FileText,
    color: 'border-red-200 bg-red-50 text-severin-red hover:bg-red-100',
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
    label: 'Менеджерский бриф',
    icon: Brain,
    color: 'border-purple-200 bg-purple-50 text-purple-700 hover:bg-purple-100',
    desc: 'Аналитика для руководителя',
  },
  risk_brief: {
    label: 'Риск-бриф',
    icon: Shield,
    color: 'border-orange-200 bg-orange-50 text-orange-700 hover:bg-orange-100',
    desc: 'Матрица рисков (PDF)',
  },
  protocol_docx: {
    label: 'Протокол (Word)',
    icon: FileText,
    color: 'border-red-200 bg-red-50 text-severin-red hover:bg-red-100',
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
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const files = Object.entries(outputFiles).filter(([fileType]) => fileType !== 'analysis');

  const handleDownload = async (fileType: string) => {
    setDownloading(fileType);
    setError(null);
    try {
      await downloadJobFile(jobId, fileType);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка скачивания');
    } finally {
      setDownloading(null);
    }
  };

  const handleDownloadAll = async () => {
    setDownloading('all');
    setError(null);
    try {
      await downloadJobFileAll(jobId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка скачивания');
    } finally {
      setDownloading(null);
    }
  };

  if (files.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        Нет файлов для скачивания
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {error && (
        <div className="sm:col-span-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}
      <button
        onClick={handleDownloadAll}
        disabled={downloading !== null}
        className="flex items-center gap-4 p-4 rounded-xl border-2 border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 transition-all sm:col-span-2 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <div className="p-2 bg-white rounded-lg shadow-sm">
          {downloading === 'all' ? (
            <Loader2 className="w-6 h-6 animate-spin" />
          ) : (
            <Archive className="w-6 h-6" />
          )}
        </div>
        <div className="flex-1 min-w-0 text-left">
          <p className="font-semibold">Скачать все файлы</p>
          <p className="text-sm opacity-70 truncate">Архив со всеми результатами</p>
        </div>
        <Download className="w-5 h-5 opacity-50" />
      </button>
      {files.map(([fileType]) => {
        const config = fileConfig[fileType] || {
          label: fileType,
          icon: FileText,
          color: 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100',
          desc: 'Файл',
        };
        const Icon = config.icon;
        const isDownloading = downloading === fileType;

        return (
          <button
            key={fileType}
            onClick={() => handleDownload(fileType)}
            disabled={downloading !== null}
            className={`flex items-center gap-4 p-4 rounded-xl border-2 transition-all ${config.color} disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <div className="p-2 bg-white rounded-lg shadow-sm">
              {isDownloading ? (
                <Loader2 className="w-6 h-6 animate-spin" />
              ) : (
                <Icon className="w-6 h-6" />
              )}
            </div>
            <div className="flex-1 min-w-0 text-left">
              <p className="font-semibold">{config.label}</p>
              <p className="text-sm opacity-70 truncate">{config.desc}</p>
            </div>
            <Download className="w-5 h-5 opacity-50" />
          </button>
        );
      })}
    </div>
  );
}
