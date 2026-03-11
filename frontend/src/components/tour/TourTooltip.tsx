import { useTourStore } from '../../stores/tourStore';

interface TourTooltipProps {
  style: React.CSSProperties;
  placement: 'top' | 'bottom' | 'left' | 'right';
  title: string;
  description: string;
}

export function TourTooltip({ style, placement, title, description }: TourTooltipProps) {
  const { currentStep, activeSteps, next, prev, finish } = useTourStore();
  const isFirst = currentStep === 0;
  const isLast = currentStep === activeSteps.length - 1;

  // Arrow position classes based on placement
  const arrowStyle: React.CSSProperties = (() => {
    const base: React.CSSProperties = {
      position: 'absolute',
      width: 0,
      height: 0,
    };
    switch (placement) {
      case 'bottom':
        return { ...base, top: -8, left: '50%', transform: 'translateX(-50%)', borderLeft: '8px solid transparent', borderRight: '8px solid transparent', borderBottom: '8px solid white' };
      case 'top':
        return { ...base, bottom: -8, left: '50%', transform: 'translateX(-50%)', borderLeft: '8px solid transparent', borderRight: '8px solid transparent', borderTop: '8px solid white' };
      case 'right':
        return { ...base, left: -8, top: '50%', transform: 'translateY(-50%)', borderTop: '8px solid transparent', borderBottom: '8px solid transparent', borderRight: '8px solid white' };
      case 'left':
        return { ...base, right: -8, top: '50%', transform: 'translateY(-50%)', borderTop: '8px solid transparent', borderBottom: '8px solid transparent', borderLeft: '8px solid white' };
    }
  })();

  return (
    <div
      className="tour-tooltip"
      style={{
        ...style,
        position: 'fixed',
        zIndex: 10002,
        width: 320,
        animation: 'tourStepTransition 0.25s ease-out',
      }}
    >
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden relative">
        {/* Arrow */}
        <div style={arrowStyle} />

        {/* Content */}
        <div className="p-4">
          <h3 className="text-base font-semibold text-slate-900 mb-1">{title}</h3>
          <p className="text-sm text-slate-600 leading-relaxed">{description}</p>
        </div>

        {/* Footer */}
        <div className="px-4 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
          <span className="text-xs text-slate-400">
            {currentStep + 1} / {activeSteps.length}
          </span>
          <div className="flex items-center gap-2">
            {!isFirst && (
              <button
                onClick={prev}
                className="px-3 py-1.5 text-sm text-slate-600 hover:text-slate-900 transition-colors"
              >
                Назад
              </button>
            )}
            {isFirst && (
              <button
                onClick={finish}
                className="px-3 py-1.5 text-sm text-slate-400 hover:text-slate-600 transition-colors"
              >
                Пропустить
              </button>
            )}
            <button
              onClick={isLast ? finish : next}
              className="px-4 py-1.5 text-sm font-medium text-white bg-severin-red hover:bg-severin-red-dark rounded-lg transition-colors"
            >
              {isLast ? 'Готово!' : 'Далее →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
