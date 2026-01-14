import { useCallback, useState } from 'react';
import { Upload, FileAudio, FileVideo, X, CheckCircle } from 'lucide-react';

interface FileDropzoneProps {
  onFileSelect: (file: File) => void;
  selectedFile: File | null;
  onClear: () => void;
}

// All FFmpeg supported audio/video formats
const ACCEPTED_TYPES = [
  // Audio
  'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav', 'audio/m4a', 'audio/x-m4a',
  'audio/aac', 'audio/ogg', 'audio/flac', 'audio/x-flac', 'audio/webm', 'audio/opus',
  'audio/amr', 'audio/3gpp', 'audio/aiff', 'audio/x-aiff', 'audio/wma', 'audio/x-ms-wma',
  // Video
  'video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo', 'video/webm',
  'video/x-matroska', 'video/x-flv', 'video/3gpp', 'video/x-ms-wmv', 'video/ogg',
];

const ACCEPTED_EXTENSIONS = '.mp3,.mp4,.wav,.m4a,.mpeg,.mov,.avi,.mkv,.webm,.flv,.ogg,.opus,.flac,.aac,.wma,.wmv,.3gp,.amr,.aiff,.ts,.mts,.m2ts';

export function FileDropzone({ onFileSelect, selectedFile, onClear }: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const file = e.dataTransfer.files[0];
      if (file && (ACCEPTED_TYPES.includes(file.type) || file.name.match(/\.(mp3|mp4|wav|m4a|mpeg|mov|avi)$/i))) {
        onFileSelect(file);
      }
    },
    [onFileSelect]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        onFileSelect(file);
      }
    },
    [onFileSelect]
  );

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const isVideo = selectedFile?.type.startsWith('video/');

  if (selectedFile) {
    return (
      <div className="w-full border-2 border-severin-red bg-gradient-to-br from-red-50 to-orange-50/50 rounded-xl p-6">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-white rounded-xl shadow-sm flex-shrink-0">
            {isVideo ? (
              <FileVideo className="w-8 h-8 text-severin-red" />
            ) : (
              <FileAudio className="w-8 h-8 text-severin-red" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="font-semibold text-slate-800 truncate">{selectedFile.name}</p>
              <CheckCircle className="w-4 h-4 text-severin-red flex-shrink-0" />
            </div>
            <p className="text-sm text-slate-500">{formatFileSize(selectedFile.size)}</p>
          </div>
          <button
            onClick={onClear}
            className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0"
            title="Удалить файл"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <label
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`
        block w-full border-2 border-dashed rounded-xl py-4 px-6 text-center cursor-pointer transition-all
        ${isDragging
          ? 'border-severin-red bg-red-50'
          : 'border-slate-300 hover:border-severin-red hover:bg-slate-50'
        }
      `}
    >
      <input
        type="file"
        accept={ACCEPTED_EXTENSIONS}
        onChange={handleFileInput}
        className="hidden"
      />

      <div className="flex items-center justify-center gap-3">
        <div className={`
          w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0
          ${isDragging ? 'bg-red-100' : 'bg-slate-100'}
        `}>
          <Upload className={`w-5 h-5 ${isDragging ? 'text-severin-red' : 'text-slate-400'}`} />
        </div>
        <div className="text-left">
          <p className="text-sm font-medium text-slate-700">
            {isDragging ? 'Отпустите файл' : 'Перетащите файл или нажмите для выбора'}
          </p>
          <p className="text-xs text-slate-500">
            MP4, MKV, AVI, MOV, WebM, FLV, MP3, WAV, M4A, AAC, FLAC, OGG, WMA и др. • до 2 ГБ
          </p>
        </div>
      </div>
    </label>
  );
}
