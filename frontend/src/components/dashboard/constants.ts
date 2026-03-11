import type { ComponentType } from 'react';
import type { LucideIcon } from 'lucide-react';
import { FileText, ListChecks, FileCheck, BarChart3, Shield, BookOpen } from 'lucide-react';
import type { JobListItem } from '../../api/client';

// Status colors for calendar events
export const STATUS_COLORS: Record<string, string> = {
  completed: '#28a745',
  processing: '#ffc107',
  pending: '#6c757d',
  failed: '#dc3545',
};

export const STATUS_LABELS: Record<string, string> = {
  completed: 'Готово',
  processing: 'В обработке',
  pending: 'В очереди',
  failed: 'Ошибка',
};

// File type display config
export const FILE_TYPE_CONFIG: Record<string, { label: string; icon: LucideIcon; description: string }> = {
  transcript: { label: 'Стенограмма', icon: FileText, description: 'Полная стенограмма (DOCX)' },
  tasks: { label: 'Excel-отчёт', icon: ListChecks, description: 'Структурированные данные (XLSX)' },
  report: { label: 'Word-отчёт', icon: FileCheck, description: 'Основной отчёт (DOCX)' },
  analysis: { label: 'Анализ', icon: BarChart3, description: 'Экспертный анализ' },
  risk_brief: { label: 'Риск-бриф', icon: Shield, description: 'Краткая сводка по рискам (PDF)' },
  summary: { label: 'Конспект', icon: BookOpen, description: 'Тематический разбор (DOCX)' },
};


// Meeting type config
export interface MeetingTypeConfig {
  id: string;
  name: string;
  icon: LucideIcon;
  color: string;
  hoverBorder: string;
  hoverBg: string;
}

// Domain dashboard config
export interface DomainConfig {
  domainId: string;
  title: string;
  headerIcon: LucideIcon;
  accentColor: AccentColor;
  meetingTypes: MeetingTypeConfig[];
  meetingGridCols?: number;
  calendarEventTitle?: 'dynamic' | string;
  DetailModal?: ComponentType<{ job: JobListItem; onClose: () => void }>;
}

// Static Tailwind color mapping (prevents dynamic class purging)
export const ACCENT_COLOR_MAP = {
  purple: {
    gradientFrom: 'from-purple-600',
    gradientTo: 'to-purple-700',
    spinnerText: 'text-purple-500',
    calendarIcon: 'text-purple-600',
    activeBg: 'bg-purple-600',
    linkText: 'text-purple-600',
    linkHover: 'hover:text-purple-700',
    iconBg: 'bg-purple-100',
    iconText: 'text-purple-600',
    processingSpinner: 'text-purple-400',
    hoverBorder: 'hover:border-purple-300',
    hoverBg: 'hover:bg-purple-50',
    groupHoverText: 'group-hover:text-purple-600',
  },
  indigo: {
    gradientFrom: 'from-indigo-600',
    gradientTo: 'to-indigo-700',
    spinnerText: 'text-indigo-500',
    calendarIcon: 'text-indigo-600',
    activeBg: 'bg-indigo-600',
    linkText: 'text-indigo-600',
    linkHover: 'hover:text-indigo-700',
    iconBg: 'bg-indigo-100',
    iconText: 'text-indigo-600',
    processingSpinner: 'text-indigo-400',
    hoverBorder: 'hover:border-indigo-300',
    hoverBg: 'hover:bg-indigo-50',
    groupHoverText: 'group-hover:text-indigo-600',
  },
  teal: {
    gradientFrom: 'from-teal-600',
    gradientTo: 'to-teal-700',
    spinnerText: 'text-teal-500',
    calendarIcon: 'text-teal-600',
    activeBg: 'bg-teal-600',
    linkText: 'text-teal-600',
    linkHover: 'hover:text-teal-700',
    iconBg: 'bg-teal-100',
    iconText: 'text-teal-600',
    processingSpinner: 'text-teal-400',
    hoverBorder: 'hover:border-teal-300',
    hoverBg: 'hover:bg-teal-50',
    groupHoverText: 'group-hover:text-teal-600',
  },
  blue: {
    gradientFrom: 'from-blue-600',
    gradientTo: 'to-blue-700',
    spinnerText: 'text-blue-500',
    calendarIcon: 'text-blue-600',
    activeBg: 'bg-blue-600',
    linkText: 'text-blue-600',
    linkHover: 'hover:text-blue-700',
    iconBg: 'bg-blue-100',
    iconText: 'text-blue-600',
    processingSpinner: 'text-blue-400',
    hoverBorder: 'hover:border-blue-300',
    hoverBg: 'hover:bg-blue-50',
    groupHoverText: 'group-hover:text-blue-600',
  },
} as const;

export type AccentColor = keyof typeof ACCENT_COLOR_MAP;
