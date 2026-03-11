/**
 * Domain Switcher Component
 *
 * Dropdown for switching between user's assigned domains.
 * Domain list is fetched from backend API; icons/colors from unified config.
 */
import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check, Lock } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import { authApi } from '../api/adminApi';
import { getDomains, type DomainInfo } from '../api/client';
import { getDomainConfig, DOMAIN_REGISTRY } from '../config/domains';
import clsx from 'clsx';

const DEFAULT_CONFIG = {
  icon: DOMAIN_REGISTRY[0].icon,
  color: 'text-slate-600 bg-slate-50',
};

export function DomainSwitcher() {
  const { user, setUser } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [allDomains, setAllDomains] = useState<DomainInfo[]>([]);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch available domains from backend
  useEffect(() => {
    getDomains()
      .then(setAllDomains)
      .catch(() => setAllDomains([]));
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Get available domains
  const userDomains = user?.domains || [];
  const activeDomain = user?.active_domain || user?.domain || userDomains[0] || 'construction';

  // Admins have access to all domains
  const isAdmin = user?.is_superuser || user?.role === 'admin';
  const accessibleDomains = new Set(isAdmin ? allDomains.map(d => d.id) : userDomains);

  // All users see all domains from backend
  const displayDomainIds = allDomains.map(d => d.id);

  // Build display list with names from backend
  const domainNameMap = Object.fromEntries(allDomains.map(d => [d.id, d.name]));

  const getConfig = (id: string) => {
    const cfg = getDomainConfig(id);
    return cfg ? { icon: cfg.icon, color: cfg.color } : DEFAULT_CONFIG;
  };
  const getDomainName = (id: string) => domainNameMap[id] || id;

  // Don't show if no user or no domains loaded
  if (!user || displayDomainIds.length === 0) {
    if (user && activeDomain) {
      const config = getConfig(activeDomain);
      const Icon = config.icon;
      return (
        <div className={clsx('flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium', config.color)}>
          <Icon className="w-3.5 h-3.5" />
          <span>{getDomainName(activeDomain)}</span>
        </div>
      );
    }
    return null;
  }

  const handleDomainChange = async (domain: string) => {
    if (domain === activeDomain || isLoading || !accessibleDomains.has(domain)) return;

    setIsLoading(true);
    try {
      const updatedUser = await authApi.setActiveDomain(domain);
      setUser(updatedUser);
      setIsOpen(false);
    } catch (error) {
      console.error('Failed to switch domain:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const currentConfig = getConfig(activeDomain);
  const CurrentIcon = currentConfig.icon;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className={clsx(
          'flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium transition-all',
          currentConfig.color,
          'hover:opacity-80',
          isLoading && 'opacity-50 cursor-wait'
        )}
      >
        <CurrentIcon className="w-3.5 h-3.5" />
        <span>{getDomainName(activeDomain)}</span>
        <ChevronDown className={clsx('w-3 h-3 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div className="absolute right-0 mt-1 w-48 bg-white border border-slate-200 rounded-lg shadow-lg z-50 overflow-hidden">
          <div className="py-1">
            <div className="px-3 py-1.5 text-[10px] text-slate-400 uppercase tracking-wider font-medium">
              Выбор домена
            </div>
            {displayDomainIds.map((domainId) => {
              const config = getConfig(domainId);
              const Icon = config.icon;
              const isActive = domainId === activeDomain;
              const hasAccess = accessibleDomains.has(domainId);

              return (
                <button
                  key={domainId}
                  onClick={() => hasAccess ? handleDomainChange(domainId) : undefined}
                  title={hasAccess ? undefined : 'Запросить доступ у администратора'}
                  className={clsx(
                    'w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors',
                    !hasAccess
                      ? 'text-slate-400 cursor-default'
                      : isActive
                        ? 'bg-slate-100 text-slate-900'
                        : 'text-slate-600 hover:bg-slate-50'
                  )}
                >
                  <Icon className={clsx('w-4 h-4', hasAccess && isActive && config.color.split(' ')[0], !hasAccess && 'text-slate-300')} />
                  <span className="flex-1 text-left">{getDomainName(domainId)}</span>
                  {isActive && hasAccess && <Check className="w-4 h-4 text-green-500" />}
                  {!hasAccess && <Lock className="w-3.5 h-3.5 text-slate-300" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
