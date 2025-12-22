import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Loader2, PlayCircle } from 'lucide-react';
import { FileDropzone } from '../components/FileDropzone';
import { ArtifactOptions, defaultArtifactState } from '../components/ArtifactOptions';
import { LanguageSelector, defaultLanguages } from '../components/LanguageSelector';
import type { ArtifactState } from '../components/ArtifactOptions';
import { createTranscription } from '../api/client';

export function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [languages, setLanguages] = useState<string[]>(defaultLanguages);
  const [artifacts, setArtifacts] = useState<ArtifactState>(defaultArtifactState);

  const mutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('No file selected');

      const response = await createTranscription(file, {
        languages: languages.join(','),
        generate_transcript: artifacts.transcript,
        generate_tasks: artifacts.tasks,
        generate_report: artifacts.report,
        generate_analysis: artifacts.analysis,
      });

      return response;
    },
    onSuccess: (data) => {
      navigate(`/job/${data.job_id}`);
    },
  });

  const hasAnyArtifact = Object.values(artifacts).some(Boolean);
  const canSubmit = file && hasAnyArtifact && !mutation.isPending;

  return (
    <div className="max-w-3xl mx-auto">
      {/* Main card */}
      <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200 overflow-hidden">
        {/* File upload section */}
        <div className="p-6 border-b border-slate-100">
          <h2 className="text-base font-semibold text-slate-800 mb-3">
            <span className="text-emerald-600">1.</span> Загрузите аудио или видео файл
          </h2>
          <FileDropzone
            onFileSelect={setFile}
            selectedFile={file}
            onClear={() => setFile(null)}
          />
        </div>

        {/* Language selector */}
        <div className="p-6 border-b border-slate-100 bg-slate-50/50">
          <h2 className="text-base font-semibold text-slate-800 mb-3">
            <span className="text-emerald-600">2.</span> Выберите языки распознавания
          </h2>
          <LanguageSelector value={languages} onChange={setLanguages} />
        </div>

        {/* Artifact options */}
        <div className="p-6 border-b border-slate-100">
          <h2 className="text-base font-semibold text-slate-800 mb-3">
            <span className="text-emerald-600">3.</span> Выберите документы для генерации
          </h2>
          <ArtifactOptions value={artifacts} onChange={setArtifacts} />
        </div>

        {/* Submit section */}
        <div className="p-6 bg-gradient-to-r from-slate-50 to-emerald-50">
          {/* Error message */}
          {mutation.isError && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 mb-4">
              {mutation.error instanceof Error ? mutation.error.message : 'Произошла ошибка при загрузке'}
            </div>
          )}

          {!hasAnyArtifact && file && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-700 mb-4 text-center">
              Выберите хотя бы один документ для генерации
            </div>
          )}

          <button
            onClick={() => mutation.mutate()}
            disabled={!canSubmit}
            className={`w-full py-3 px-6 rounded-xl font-semibold text-white transition-all flex items-center justify-center gap-2 ${
              canSubmit
                ? 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40'
                : 'bg-slate-300 cursor-not-allowed'
            }`}
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Загрузка...
              </>
            ) : (
              <>
                <PlayCircle className="w-5 h-5" />
                Обработать
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
