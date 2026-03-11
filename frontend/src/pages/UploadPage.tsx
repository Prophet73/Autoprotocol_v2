import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Loader2, PlayCircle, Check, X, Mail, Calendar, LogIn, Shield, EyeOff, Users, ChevronRight } from 'lucide-react';
import { FileDropzone } from '../components/FileDropzone';
import { ArtifactOptions, defaultArtifactState } from '../components/ArtifactOptions';
import { LanguageSelector, defaultLanguages } from '../components/LanguageSelector';
import { MeetingTypeSelector } from '../components/MeetingTypeSelector';
import { ParticipantModal } from '../components/ParticipantModal';
import type { ArtifactState } from '../components/ArtifactOptions';
import { createTranscription, validateProjectCode, getProjectContractors } from '../api/client';
import { useAuthStore } from '../stores/authStore';

// Login prompt component for unauthenticated users
function LoginPrompt() {
  const [isLoading, setIsLoading] = useState(false);

  const handleSSOLogin = () => {
    setIsLoading(true);
    // Redirect to Hub SSO with return to home page
    window.location.href = '/auth/hub/login?redirect_to=/';
  };

  return (
    <div className="max-w-xl mx-auto">
      <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-8 text-center bg-gradient-to-r from-slate-50 to-red-50/30 border-b border-slate-100">
          <div className="w-16 h-16 bg-severin-red/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <Shield className="w-8 h-8 text-severin-red" />
          </div>
          <h1 className="text-2xl font-bold text-slate-800 mb-2">
            Требуется авторизация
          </h1>
          <p className="text-slate-600">
            Для загрузки файлов и создания протоколов необходимо войти в систему
          </p>
        </div>

        {/* Features list */}
        <div className="px-6 py-6 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-800 mb-3">
            Возможности сервиса:
          </h2>
          <ul className="space-y-2 text-sm text-slate-600">
            <li className="flex items-start gap-2">
              <Check className="w-4 h-4 text-severin-red mt-0.5 flex-shrink-0" />
              <span>Автоматическая расшифровка аудио и видео записей совещаний</span>
            </li>
            <li className="flex items-start gap-2">
              <Check className="w-4 h-4 text-severin-red mt-0.5 flex-shrink-0" />
              <span>Генерация протоколов с выделением ключевых решений и задач</span>
            </li>
            <li className="flex items-start gap-2">
              <Check className="w-4 h-4 text-severin-red mt-0.5 flex-shrink-0" />
              <span>Отправка готовых отчётов на email</span>
            </li>
          </ul>
        </div>

        {/* Login button */}
        <div className="px-6 py-6 bg-slate-50/50">
          <button
            onClick={handleSSOLogin}
            disabled={isLoading}
            className="w-full py-3 px-6 rounded-lg font-semibold text-white bg-severin-red hover:bg-severin-red-dark shadow-lg shadow-severin-red/25 hover:shadow-severin-red/40 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Перенаправление...
              </>
            ) : (
              <>
                <LogIn className="w-5 h-5" />
                Войти через корпоративный SSO
              </>
            )}
          </button>
          <p className="text-xs text-slate-500 mt-3 text-center">
            Используйте вашу корпоративную учётную запись для входа
          </p>
        </div>
      </div>
    </div>
  );
}

export function UploadPage() {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuthStore();

  // All hooks must be called unconditionally at the top
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
  // Meeting date (optional)
  const [meetingDate, setMeetingDate] = useState('');
  // Use active_domain (from domain switcher) or fall back to first domain or 'construction'
  const userDomain = user?.active_domain || user?.domain || (user?.domains?.[0]) || 'construction';
  const showMeetingTypeSelector = userDomain !== 'construction' && userDomain !== 'fta';
  // For construction and FTA, show project code input
  const showProjectCodeRequired = userDomain === 'construction' || userDomain === 'fta';

  // Reset invalid artifacts when domain changes
  useEffect(() => {
    setArtifacts((prev) => {
      const next = { ...prev };
      // summary is only valid for construction/fta
      if (!showProjectCodeRequired && next.summary) {
        next.summary = false;
      }
      // risk_brief is always generated automatically — no user toggle needed
      return next;
    });
  }, [userDomain]); // eslint-disable-line react-hooks/exhaustive-deps

  // Email notification (optional)
  const [notifyEmails, setNotifyEmails] = useState('');

  // Private record (hidden from department calendar)
  const [isPrivate, setIsPrivate] = useState(false);

  // Upload progress tracking
  const [uploadProgress, setUploadProgress] = useState(0);

  // Meeting participants
  const [selectedParticipants, setSelectedParticipants] = useState<number[]>([]);
  const [showParticipantModal, setShowParticipantModal] = useState(false);
  const [participantSummary, setParticipantSummary] = useState('');

  // Validate project code when it changes
  useEffect(() => {
    if (!isAuthenticated) return; // Skip if not authenticated
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
  }, [projectCode, isAuthenticated]);

  // Update participant summary when selection changes
  useEffect(() => {
    if (!codeValidation?.valid || selectedParticipants.length === 0) {
      setParticipantSummary('');
      return;
    }
    // Fetch contractors to build summary
    getProjectContractors(projectCode).then((contractors) => {
      const parts: string[] = [];
      for (const c of contractors) {
        const count = c.persons.filter((p) => selectedParticipants.includes(p.id)).length;
        if (count > 0) parts.push(`${c.organization_name} (${count})`);
      }
      setParticipantSummary(parts.join(', '));
    }).catch(() => setParticipantSummary(`${selectedParticipants.length} чел.`));
  }, [selectedParticipants, codeValidation?.valid, projectCode]);

  const handleCodeChange = (value: string) => {
    // Only allow digits, max 4
    const digits = value.replace(/\D/g, '').slice(0, 4);
    setProjectCode(digits);
  };

  // Handle file selection and auto-fill meeting date from file metadata
  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile);

    // Auto-fill meeting date from file's lastModified timestamp
    if (selectedFile.lastModified) {
      const date = new Date(selectedFile.lastModified);
      // Format as YYYY-MM-DD for input type="date"
      const formattedDate = date.toISOString().split('T')[0];
      setMeetingDate(formattedDate);
    }
  };

  const handleFileClear = () => {
    setFile(null);
    setMeetingDate('');
  };

  const mutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('No file selected');
      // Only require valid project code for construction domain
      if (showProjectCodeRequired && !codeValidation?.valid) {
        throw new Error('Invalid project code');
      }

      setUploadProgress(0);
      const response = await createTranscription(file, {
        languages: languages.join(','),
        domain: userDomain,  // Pass current domain
        generate_transcript: artifacts.transcript,
        generate_tasks: artifacts.tasks,
        generate_report: artifacts.report,
        generate_summary: artifacts.summary,
        generate_risk_brief: userDomain === 'construction',  // Risk brief only for construction
        // Only send project_code if it's valid (for construction or if manually entered for other domains)
        project_code: codeValidation?.valid ? projectCode : undefined,
        meeting_type: showMeetingTypeSelector ? meetingType : undefined,
        meeting_date: meetingDate || undefined,
        notify_emails: notifyEmails.trim() || undefined,
        participant_ids: selectedParticipants.length > 0 ? selectedParticipants : undefined,
        is_private: isPrivate || undefined,
      }, setUploadProgress);

      return response;
    },
    onSuccess: (data) => {
      setUploadProgress(0);
      navigate(`/job/${data.job_id}`);
    },
    onError: () => {
      setUploadProgress(0);
    },
  });

  const hasAnyArtifact = Object.values(artifacts).some(Boolean);
  // Project code is only required for construction domain
  const isCodeValid = showProjectCodeRequired ? codeValidation?.valid === true : true;
  const isMeetingTypeValid = !showMeetingTypeSelector || meetingType !== '';
  const canSubmit = file && hasAnyArtifact && isCodeValid && isMeetingTypeValid && !mutation.isPending;

  // Show login prompt for unauthenticated users (after all hooks)
  if (!isAuthenticated) {
    return <LoginPrompt />;
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Main card */}
      <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200 overflow-hidden">
        {/* Project code section - required for construction, optional for HR/IT */}
        {showProjectCodeRequired ? (
        <div className="px-5 py-3 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-red-50/30" data-tour="project-code">
          <h2 className="text-sm font-semibold text-slate-800 mb-2">
            <span className="text-severin-red">1.</span> Введите код проекта и дату встречи
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
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
              <input
                type="date"
                value={meetingDate}
                onChange={(e) => setMeetingDate(e.target.value)}
                className="w-40 pl-10 pr-3 py-2 border-2 border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-severin-red focus:border-transparent"
              />
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
        ) : null}

        {/* Participant selector button (for construction/fta domains) */}
        {showProjectCodeRequired && (
          <div className="px-5 py-3 border-b border-slate-100">
            <button
              type="button"
              onClick={() => setShowParticipantModal(true)}
              className="w-full flex items-center gap-3 px-4 py-2.5 border-2 border-dashed border-slate-300 rounded-lg text-sm text-slate-600 hover:border-severin-red hover:bg-red-50/50 hover:text-slate-800 transition-all group cursor-pointer"
            >
              <Users className="w-5 h-5 text-slate-400 group-hover:text-severin-red transition-colors" />
              <span className="font-medium">Участники совещания</span>
              {selectedParticipants.length > 0 ? (
                <span className="bg-severin-red text-white px-2 py-0.5 rounded-full text-xs font-medium">
                  {selectedParticipants.length}
                </span>
              ) : (
                <span className="text-xs text-slate-400">необязательно</span>
              )}
              {participantSummary && (
                <span className="text-xs text-slate-400 truncate ml-auto mr-1 max-w-[200px]">
                  {participantSummary}
                </span>
              )}
              <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-severin-red ml-auto transition-colors" />
            </button>
          </div>
        )}

        {/* Participant modal */}
        {showParticipantModal && (
          <ParticipantModal
            projectCode={projectCode}
            selectedPersonIds={selectedParticipants}
            onChange={setSelectedParticipants}
            onClose={() => setShowParticipantModal(false)}
          />
        )}

        {/* Meeting type selector (for non-construction domains) */}
        {showMeetingTypeSelector && (
          <div className="px-5 py-3 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-purple-50/30">
            <h2 className="text-sm font-semibold text-slate-800 mb-2">
              <span className="text-severin-red">1.</span> Выберите тип и дату встречи
            </h2>
            <div className="flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <MeetingTypeSelector
                  domain={userDomain}
                  value={meetingType}
                  onChange={setMeetingType}
                />
              </div>
              <div className="relative flex-shrink-0">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                <input
                  type="date"
                  value={meetingDate}
                  onChange={(e) => setMeetingDate(e.target.value)}
                  className="w-44 pl-10 pr-3 py-2 border-2 border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-severin-red focus:border-transparent"
                />
              </div>
            </div>
          </div>
        )}

        {/* File upload section */}
        <div className="px-5 py-3 border-b border-slate-100" data-tour="dropzone">
          <h2 className="text-sm font-semibold text-slate-800 mb-2">
            <span className="text-severin-red">2.</span> Загрузите аудио или видео файл
          </h2>
          <FileDropzone
            onFileSelect={handleFileSelect}
            selectedFile={file}
            onClear={handleFileClear}
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
        <div className="px-5 py-3 border-b border-slate-100" data-tour="artifact-options">
          <h2 className="text-sm font-semibold text-slate-800 mb-2">
            <span className="text-severin-red">4.</span> Выберите документы для генерации
          </h2>
          <ArtifactOptions
            value={artifacts}
            onChange={setArtifacts}
            showSummary={showProjectCodeRequired}
          />
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

        {/* Private record toggle — only for DCT and Business domains */}
        {isAuthenticated && (userDomain === 'dct' || userDomain === 'business') && (
          <div className="px-5 py-3 border-b border-slate-100">
            <label className="flex items-center gap-3 cursor-pointer group">
              <div
                className={`relative w-9 h-5 rounded-full transition-colors ${
                  isPrivate ? 'bg-severin-red' : 'bg-slate-300'
                }`}
                onClick={() => setIsPrivate(!isPrivate)}
              >
                <div
                  className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                    isPrivate ? 'translate-x-4' : ''
                  }`}
                />
              </div>
              <div className="flex items-center gap-2">
                <EyeOff className={`w-4 h-4 ${isPrivate ? 'text-severin-red' : 'text-slate-400'}`} />
                <span className="text-sm font-medium text-slate-700">Личная запись</span>
              </div>
              <span className="text-xs text-slate-400 ml-auto">Видна только вам</span>
            </label>
          </div>
        )}

        {/* Submit section */}
        <div className="px-5 py-4 bg-gradient-to-r from-slate-50 to-red-50/50">
          {/* Error message */}
          {mutation.isError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm mb-3">
              {mutation.error instanceof Error ? mutation.error.message : 'Произошла ошибка при загрузке'}
            </div>
          )}

          {showProjectCodeRequired && !isCodeValid && file && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-sm mb-3 text-center">
              Введите корректный код проекта (4 цифры)
            </div>
          )}

          {showMeetingTypeSelector && !isMeetingTypeValid && file && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-sm mb-3 text-center">
              Выберите тип встречи
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
                Загрузка... {uploadProgress > 0 && uploadProgress < 100 ? `${uploadProgress}%` : ''}
              </>
            ) : (
              <>
                <PlayCircle className="w-5 h-5" />
                Обработать
              </>
            )}
          </button>

          {/* Upload progress bar */}
          {mutation.isPending && uploadProgress > 0 && (
            <div className="mt-3">
              <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-severin-red rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-xs text-slate-500 mt-1 text-center">
                {uploadProgress < 100 ? `Загрузка файла: ${uploadProgress}%` : 'Файл загружен, обработка...'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
