/**
 * Meeting Type Selector Component
 *
 * Dropdown selector for meeting type based on user's domain.
 * Shows name and description for each option.
 */
import { useState, useEffect } from 'react';
import { ChevronDown, Briefcase, Check, Loader2 } from 'lucide-react';
import { getMeetingTypes } from '../api/client';
import type { MeetingTypeInfo } from '../api/client';

interface MeetingTypeSelectorProps {
  domain: string | null;
  value: string;
  onChange: (meetingType: string) => void;
}

export function MeetingTypeSelector({ domain, value, onChange }: MeetingTypeSelectorProps) {
  const [meetingTypes, setMeetingTypes] = useState<MeetingTypeInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  // Fetch meeting types when domain changes
  useEffect(() => {
    if (domain && domain !== 'construction') {
      setIsLoading(true);
      getMeetingTypes(domain)
        .then((types) => {
          setMeetingTypes(types);
          // Set default value if not already set
          if (!value && types.length > 0) {
            const defaultType = types.find(t => t.default) || types[0];
            onChange(defaultType.id);
          }
        })
        .catch((err) => {
          console.error('Failed to fetch meeting types:', err);
          setMeetingTypes([]);
        })
        .finally(() => setIsLoading(false));
    } else {
      setMeetingTypes([]);
    }
  }, [domain]);

  // Don't render for construction domain or when no domain
  if (!domain || domain === 'construction') {
    return null;
  }

  const selectedType = meetingTypes.find(t => t.id === value);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading || meetingTypes.length === 0}
        className="w-full h-10 flex items-center justify-between gap-2 px-4 bg-white border border-slate-300 rounded-lg text-left hover:border-severin-red focus:outline-none focus:ring-2 focus:ring-severin-red focus:border-transparent transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <div className="flex items-center gap-2 min-w-0">
          <Briefcase className="w-4 h-4 text-slate-400 flex-shrink-0" />
          {isLoading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 text-slate-400 animate-spin" />
              <span className="text-slate-400 text-sm">Загрузка...</span>
            </div>
          ) : selectedType ? (
            <span className="text-sm text-slate-800 truncate">{selectedType.name}</span>
          ) : (
            <span className="text-slate-400 text-sm">Выберите тип встречи</span>
          )}
        </div>
        <ChevronDown className={`w-4 h-4 text-slate-400 flex-shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && meetingTypes.length > 0 && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          <div className="absolute z-20 left-0 w-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg overflow-hidden">
            {meetingTypes.map((type) => (
              <button
                key={type.id}
                type="button"
                onClick={() => {
                  onChange(type.id);
                  setIsOpen(false);
                }}
                className={`w-full px-4 py-2.5 text-left hover:bg-slate-50 transition-colors flex items-center justify-between ${
                  type.id === value ? 'bg-red-50' : ''
                }`}
              >
                <div>
                  <div className={`text-sm ${type.id === value ? 'text-severin-red font-medium' : 'text-slate-700'}`}>
                    {type.name}
                  </div>
                  {type.description && (
                    <div className="text-xs text-slate-400">{type.description}</div>
                  )}
                </div>
                {type.id === value && (
                  <Check className="w-4 h-4 text-severin-red flex-shrink-0" />
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default MeetingTypeSelector;
