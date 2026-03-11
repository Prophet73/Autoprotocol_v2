/**
 * Единый реестр доменов.
 *
 * Все компоненты должны использовать этот файл вместо хардкода названий,
 * иконок, цветов и маппинга на дашборды.
 *
 * Добавление нового домена = добавление одной записи в DOMAIN_REGISTRY.
 */
import { lazy, type ComponentType, type LazyExoticComponent } from 'react';
import {
  Building2,
  Monitor,
  FileCheck,
  Briefcase,
  Landmark,
  type LucideIcon,
} from 'lucide-react';

// ============================================================================
// Типы
// ============================================================================

export interface DomainConfig {
  /** Уникальный id домена (совпадает с бэкендом) */
  id: string;
  /** Отображаемое название */
  label: string;
  /** Иконка lucide-react */
  icon: LucideIcon;
  /** Tailwind-классы для DomainSwitcher (текст + фон) */
  color: string;
  /** Tailwind-класс точки-индикатора (Layout sidebar) */
  dotColor: string;
  /** Tailwind-классы бэджа в таблицах */
  badgeClasses: string;
  /** Lazy-loaded компонент дашборда */
  dashboard: LazyExoticComponent<ComponentType>;
  /** Путь в роутере (без /dashboard/ префикса) */
  routePath: string;
}

// ============================================================================
// Lazy-loaded дашборды
// ============================================================================

const ManagerDashboardPage = lazy(() =>
  import('../pages/ManagerDashboardPage').then(m => ({ default: m.ManagerDashboardPage }))
);
const DCTDashboardPage = lazy(() =>
  import('../pages/DCTDashboardPage').then(m => ({ default: m.DCTDashboardPage }))
);
const FTADashboardPage = lazy(() =>
  import('../pages/FTADashboardPage').then(m => ({ default: m.FTADashboardPage }))
);
const BusinessDashboardPage = lazy(() =>
  import('../pages/BusinessDashboardPage').then(m => ({ default: m.BusinessDashboardPage }))
);
const CEODashboardPage = lazy(() =>
  import('../pages/CEODashboardPage').then(m => ({ default: m.CEODashboardPage }))
);

// ============================================================================
// Реестр доменов — ЕДИНСТВЕННЫЙ ИСТОЧНИК ПРАВДЫ на фронтенде
// ============================================================================

export const DOMAIN_REGISTRY: DomainConfig[] = [
  {
    id: 'construction',
    label: 'ДПУ',
    icon: Building2,
    color: 'text-amber-600 bg-amber-50',
    dotColor: 'bg-amber-500',
    badgeClasses: 'bg-orange-100 text-orange-700',
    dashboard: ManagerDashboardPage,
    routePath: 'construction',
  },
  {
    id: 'dct',
    label: 'ДЦТ',
    icon: Monitor,
    color: 'text-blue-600 bg-blue-50',
    dotColor: 'bg-blue-500',
    badgeClasses: 'bg-cyan-100 text-cyan-700',
    dashboard: DCTDashboardPage,
    routePath: 'dct',
  },
  {
    id: 'fta',
    label: 'ДФТА',
    icon: FileCheck,
    color: 'text-teal-600 bg-teal-50',
    dotColor: 'bg-teal-500',
    badgeClasses: 'bg-teal-100 text-teal-700',
    dashboard: FTADashboardPage,
    routePath: 'fta',
  },
  {
    id: 'business',
    label: 'Бизнес',
    icon: Briefcase,
    color: 'text-indigo-600 bg-indigo-50',
    dotColor: 'bg-indigo-500',
    badgeClasses: 'bg-indigo-100 text-indigo-700',
    dashboard: BusinessDashboardPage,
    routePath: 'business',
  },
  {
    id: 'ceo',
    label: 'CEO',
    icon: Landmark,
    color: 'text-purple-600 bg-purple-50',
    dotColor: 'bg-purple-500',
    badgeClasses: 'bg-purple-100 text-purple-700',
    dashboard: CEODashboardPage,
    routePath: 'ceo',
  },
];

// ============================================================================
// Удобные хелперы
// ============================================================================

/** Быстрый lookup по id */
const _byId = new Map(DOMAIN_REGISTRY.map(d => [d.id, d]));

/** Получить конфиг домена по id */
export function getDomainConfig(domainId: string): DomainConfig | undefined {
  return _byId.get(domainId);
}

/** Получить отображаемое название домена */
export function getDomainLabel(domainId: string): string {
  return _byId.get(domainId)?.label ?? domainId;
}

/** Получить иконку домена */
export function getDomainIcon(domainId: string): LucideIcon {
  return _byId.get(domainId)?.icon ?? Building2;
}

/** Массив {value, label} для select/dropdown (обратная совместимость) */
export const AVAILABLE_DOMAINS = DOMAIN_REGISTRY.map(d => ({
  value: d.id,
  label: d.label,
}));

/** Словарь id → label */
export const DOMAIN_LABELS: Record<string, string> = Object.fromEntries(
  DOMAIN_REGISTRY.map(d => [d.id, d.label])
);
