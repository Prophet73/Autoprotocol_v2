/**
 * Domain Switcher Component
 *
 * Dropdown for switching between user's assigned domains.
 * Only shown for users with multiple domains.
 */
import { useState, useRef, useEffect } from 'react';
import { Building2, Monitor, ChevronDown, Check } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import { authApi } from '../api/adminApi';
import clsx from 'clsx';

// Domain display configuration
const DOMAIN_CONFIG: Record<string, { label: string; icon: typeof Building2; color: string }> = {
  construction: {
    label: 'Construction',
    icon: Building2,
    color: 'text-amber-600 bg-amber-50',
  },
  dct: {
    label: 'ДЦТ',
    icon: Monitor,
    color: 'text-blue-600 bg-blue-50',
  },
  general: {
    label: 'General',
    icon: Building2,
    color: 'text-slate-600 bg-slate-50',
  },
};

export function DomainSwitcher() {
  const { user, setUser } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

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
  const availableDomains = user?.domains || [];
  const activeDomain = user?.active_domain || user?.domain || availableDomains[0] || 'construction';

  // If superuser, show all domains
  const displayDomains = user?.is_superuser
    ? ['construction', 'dct']
    : availableDomains;

  // Don't show if user has only one domain
  if (!user || displayDomains.length <= 1) {
    // Show just a badge for single domain
    if (user && activeDomain) {
      const config = DOMAIN_CONFIG[activeDomain] || DOMAIN_CONFIG.general;
      const Icon = config.icon;
      return (
        <div className={clsx('flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium', config.color)}>
          <Icon className="w-3.5 h-3.5" />
          <span>{config.label}</span>
        </div>
      );
    }
    return null;
  }

  const handleDomainChange = async (domain: string) => {
    if (domain === activeDomain || isLoading) return;

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

  const currentConfig = DOMAIN_CONFIG[activeDomain] || DOMAIN_CONFIG.general;
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
        <span>{currentConfig.label}</span>
        <ChevronDown className={clsx('w-3 h-3 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div className="absolute right-0 mt-1 w-40 bg-white border border-slate-200 rounded-lg shadow-lg z-50 overflow-hidden">
          <div className="py-1">
            <div className="px-3 py-1.5 text-[10px] text-slate-400 uppercase tracking-wider font-medium">
              Select Domain
            </div>
            {displayDomains.map((domain) => {
              const config = DOMAIN_CONFIG[domain] || DOMAIN_CONFIG.general;
              const Icon = config.icon;
              const isActive = domain === activeDomain;

              return (
                <button
                  key={domain}
                  onClick={() => handleDomainChange(domain)}
                  className={clsx(
                    'w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors',
                    isActive
                      ? 'bg-slate-100 text-slate-900'
                      : 'text-slate-600 hover:bg-slate-50'
                  )}
                >
                  <Icon className={clsx('w-4 h-4', isActive && config.color.split(' ')[0])} />
                  <span className="flex-1 text-left">{config.label}</span>
                  {isActive && <Check className="w-4 h-4 text-green-500" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
