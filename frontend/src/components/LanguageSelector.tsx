import { useState } from 'react';
import { Check, ChevronDown } from 'lucide-react';

export interface Language {
  code: string;
  name: string;
  flag: string;
}

export const AVAILABLE_LANGUAGES: Language[] = [
  { code: 'ru', name: 'Русский', flag: '🇷🇺' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'zh', name: '中文', flag: '🇨🇳' },
  { code: 'ar', name: 'العربية', flag: '🇸🇦' },
  { code: 'tr', name: 'Türkçe', flag: '🇹🇷' },
];

interface LanguageSelectorProps {
  value: string[];
  onChange: (languages: string[]) => void;
}

export function LanguageSelector({ value, onChange }: LanguageSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);

  const toggleLanguage = (code: string) => {
    if (value.includes(code)) {
      if (value.length > 1) {
        onChange(value.filter((l) => l !== code));
      }
    } else {
      onChange([...value, code]);
    }
  };

  const selectedLanguages = AVAILABLE_LANGUAGES.filter((l) =>
    value.includes(l.code)
  );

  return (
    <div className="relative">
      {/* Selected languages display / trigger */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`
          w-full flex items-center justify-between px-4 py-3 bg-white border-2 rounded-xl
          transition-all text-left
          ${isOpen ? 'border-severin-red ring-2 ring-red-100' : 'border-slate-200 hover:border-slate-300'}
        `}
      >
        <div className="flex items-center gap-2 flex-wrap">
          {selectedLanguages.map((lang) => (
            <span
              key={lang.code}
              className="inline-flex items-center gap-1.5 px-3 py-1 bg-red-50 text-severin-red rounded-lg text-sm font-medium"
            >
              <span>{lang.flag}</span>
              <span>{lang.name}</span>
            </span>
          ))}
        </div>
        <ChevronDown
          className={`w-5 h-5 text-slate-400 transition-transform flex-shrink-0 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-10 w-full mt-2 border border-slate-200 rounded-xl bg-white shadow-lg overflow-hidden">
          {AVAILABLE_LANGUAGES.map((lang) => {
            const isSelected = value.includes(lang.code);
            const isOnlyOne = value.length === 1 && isSelected;

            return (
              <button
                key={lang.code}
                type="button"
                onClick={() => toggleLanguage(lang.code)}
                disabled={isOnlyOne}
                className={`
                  w-full flex items-center justify-between px-4 py-3 text-left transition-colors
                  ${isSelected ? 'bg-red-50' : 'hover:bg-slate-50'}
                  ${isOnlyOne ? 'opacity-50 cursor-not-allowed' : ''}
                `}
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">{lang.flag}</span>
                  <span className="font-medium text-slate-700">{lang.name}</span>
                  <span className="text-slate-400 text-sm">({lang.code})</span>
                </div>
                {isSelected && <Check className="w-5 h-5 text-severin-red" />}
              </button>
            );
          })}
        </div>
      )}

    </div>
  );
}

export const defaultLanguages = ['ru'];
