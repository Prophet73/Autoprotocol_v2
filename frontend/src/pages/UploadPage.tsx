import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Loader2, PlayCircle, Check, X, Mail } from 'lucide-react';
import { FileDropzone } from '../components/FileDropzone';
import { ArtifactOptions, defaultArtifactState } from '../components/ArtifactOptions';
import { LanguageSelector, defaultLanguages } from '../components/LanguageSelector';
import { MeetingTypeSelector } from '../components/MeetingTypeSelector';
import type { ArtifactState } from '../components/ArtifactOptions';
import { createTranscription, validateProjectCode } from '../api/client';
import { useAuthStore } from '../stores/authStore';

export function UploadPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [file, setFile] = useState<File | null>(null);
  const [languages, setLanguages] = useState<string[]>(defaultLanguages);
  const [artifacts, setArtifacts] = useState<ArtifactState>(defaultArtifactState);

  // Project code state for Drop Box workflow
  const [projectCode, setProjectCode] = useState('');
  const [codeValidation, setCodeValidation] = useState<{
    valid: boolean;
    message: string;
    projectName?: string;
  } | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  // Meeting type for HR/IT domains
  const [meetingType, setMeetingType] = useState('');
  const userDomain = user?.domain || 'construction';
  const showMeetingTypeSelector = userDomain !== 'construction';

  // Email notification (optional)
  const [notifyEmails, setNotifyEmails] = useState('');

  // Validate project code when it changes
  useEffect(() => {
    if (projectCode.length === 4 && /^\d{4}$/.test(projectCode)) {
      setIsValidating(true);
      validateProjectCode(projectCode)
        .then((result) => {
          setCodeValidation({
            valid: result.valid,
            message: result.message,
            projectName: result.project_name,
          });
        })
        .finally(() => setIsValidating(false));
    } else if (projectCode.length > 0 && projectCode.length < 4) {
      setCodeValidation(null);
    } else if (projectCode.length === 0) {
      setCodeValidation(null);
    }
  }, [projectCode]);

  const handleCodeChange = (value: string) => {
    // Only allow digits, max 4
    const digits = value.replace(/\D/g, '').slice(0, 4);
    setProjectCode(digits);
  };

  const mutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('No file selected');
      if (!codeValidation?.valid) throw new Error('Invalid project code');

      const response = await createTranscription(file, {
        languages: languages.join(','),
        generate_transcript: artifacts.transcript,
        generate_tasks: artifacts.tasks,
        generate_report: artifacts.report,
        generate_analysis: artifacts.analysis,
        project_code: projectCode,
        meeting_type: showMeetingTypeSelector ? meetingType : undefined,
        notify_emails: notifyEmails.trim() || undefined,
      });

      return response;
    },
    onSuccess: (data) => {
      navigate(`/job/${data.job_id}`);
    },
  });

  const hasAnyArtifact = Object.values(artifacts).some(Boolean);
  const isCodeValid = codeValidation?.valid === true;
  const isMeetingTypeValid = !showMeetingTypeSelector || meetingType !== '';
  const canSubmit = file && hasAnyArtifact && isCodeValid && isMeetingTypeValid && !mutation.isPending;

  return (
    <div className="max-w-3xl mx-auto">
      {/* Main card */}
      <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200 overflow-hidden">
        {/* Project code section */}
        <div className="px-5 py-3 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-red-50/30">
          <h2 className="text-sm font-semibold text-slate-800 mb-2">
            <span className="text-severin-red">1.</span> Введите код проекта
          </h2>
          <div className="flex items-center gap-4">
            <div className="relative">
              <input
                type="text"
                inputMode="numeric"
                maxLength={4}
                placeholder="0000"
                value={projectCode}
                onChange={(e) => handleCodeChange(e.target.value)}
                className={`w-28 text-center text-xl tracking-[0.4em] font-mono border-2 rounded-lg py-2 px-3 transition-colors ${
                  codeValidation?.valid === true
                    ? 'border-severin-red bg-red-50'
                    : codeValidation?.valid === false
                    ? 'border-red-400 bg-red-50'
                    : 'border-slate-300 bg-white'
                }`}
              />
              {isValidating && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />
                </div>
              )}
              {!isValidating && codeValidation?.valid === true && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <Check className="w-5 h-5 text-severin-red" />
                </div>
              )}
              {!isValidating && codeValidation?.valid === false && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <X className="w-5 h-5 text-red-500" />
                </div>
              )}
            </div>
            <div className="flex-1">
              {codeValidation?.valid === true && codeValidation.projectName && (
                <div className="text-severin-red font-medium">
                  {codeValidation.projectName}
                </div>
              )}
              {codeValidation?.valid === false && (
                <div className="text-red-600 text-sm">
                  {codeValidation.message}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Meeting type selector (for HR/IT domains) */}
        {showMeetingTypeSelector && (
          <div className="px-5 py-3 border-b border-slate-100 bg-slate-50/50">
            <h2 className="text-sm font-semibold text-slate-800 mb-2">
              <span className="text-severin-red">1.5</span> Выберите тип встречи
            </h2>
            <MeetingTypeSelector
              domain={userDomain}
              value={meetingType}
              onChange={setMeetingType}
            />
          </div>
        )}

        {/* File upload section */}
        <div className="px-5 py-3 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-800 mb-2">
            <span className="text-severin-red">2.</span> Загрузите аудио или видео файл
          </h2>
          <FileDropzone
            onFileSelect={setFile}
            selectedFile={file}
            onClear={() => setFile(null)}
          />
        </div>

        {/* Language selector */}
        <div className="px-5 py-3 border-b border-slate-100 bg-slate-50/50">
          <h2 className="text-sm font-semibold text-slate-800 mb-2">
            <span className="text-severin-red">3.</span> Выберите языки распознавания
          </h2>
          <LanguageSelector value={languages} onChange={setLanguages} />
        </div>

        {/* Artifact options */}
        <div className="px-5 py-3 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-800 mb-2">
            <span className="text-severin-red">4.</span> Выберите документы для генерации
          </h2>
          <ArtifactOptions value={artifacts} onChange={setArtifacts} />
        </div>

        {/* Email notification (optional) */}
        <div className="px-5 py-3 border-b border-slate-100 bg-slate-50/50">
          <h2 className="text-sm font-semibold text-slate-800 mb-2">
            <span className="text-severin-red">5.</span> Отправить отчёты на почту
            <span className="text-slate-400 font-normal ml-2">(необязательно)</span>
          </h2>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="email@example.com, другой@example.com"
              value={notifyEmails}
              onChange={(e) => setNotifyEmails(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-severin-red focus:border-transparent"
            />
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Укажите email-адреса через запятую для получения готовых отчётов
          </p>
        </div>

        {/* Submit section */}
        <div className="px-5 py-4 bg-gradient-to-r from-slate-50 to-red-50/50">
          {/* Error message */}
          {mutation.isError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm mb-3">
              {mutation.error instanceof Error ? mutation.error.message : 'Произошла ошибка при загрузке'}
            </div>
          )}

          {!isCodeValid && file && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-sm mb-3 text-center">
              Введите корректный код проекта (4 цифры)
            </div>
          )}

          {!hasAnyArtifact && file && isCodeValid && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-sm mb-3 text-center">
              Выберите хотя бы один документ для генерации
            </div>
          )}

          <button
            onClick={() => mutation.mutate()}
            disabled={!canSubmit}
            className={`w-full py-2.5 px-6 rounded-lg font-semibold text-white transition-all flex items-center justify-center gap-2 ${
              canSubmit
                ? 'bg-severin-red hover:bg-severin-red-dark shadow-lg shadow-severin-red/25 hover:shadow-severin-red/40'
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
