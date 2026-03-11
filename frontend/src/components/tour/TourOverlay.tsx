import { useEffect, useState, useCallback } from 'react';
import { useTourStore } from '../../stores/tourStore';
import { TourTooltip } from './TourTooltip';

interface TourOverlayProps {
  navigate: (path: string) => void;
}

interface SpotlightRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

const PADDING = 8;
const TOOLTIP_GAP = 12;

export function TourOverlay({ navigate }: TourOverlayProps) {
  const { isActive, currentStep, activeSteps, next, prev, finish } = useTourStore();
  const [spotlight, setSpotlight] = useState<SpotlightRect | null>(null);
  const [tooltipStyle, setTooltipStyle] = useState<React.CSSProperties>({});
  const [visible, setVisible] = useState(false);

  const step = activeSteps[currentStep];

  // Navigate to step path if needed
  useEffect(() => {
    if (!isActive || !step?.path) return;
    const currentPath = window.location.pathname;
    if (step.path !== currentPath) {
      navigate(step.path);
    }
  }, [isActive, currentStep, step, navigate]);

  // Find and spotlight the target element
  const updateSpotlight = useCallback(() => {
    if (!isActive || !step) {
      setSpotlight(null);
      return;
    }

    // Try to find the target element with retries (async data may not be loaded yet)
    let attempt = 0;
    const maxAttempts = 5;
    const delays = [200, 400, 800, 1200, 2000];

    const positionSpotlight = (el: Element) => {
      const rect = el.getBoundingClientRect();
      const sr: SpotlightRect = {
        x: rect.left - PADDING,
        y: rect.top - PADDING,
        width: rect.width + PADDING * 2,
        height: rect.height + PADDING * 2,
      };
      setSpotlight(sr);

      const tooltipWidth = 320;
      const tooltipEstHeight = 160;
      const vw = window.innerWidth;
      const vh = window.innerHeight;

      let top = 0;
      let left = 0;
      const placement = step.placement;

      switch (placement) {
        case 'bottom':
          top = sr.y + sr.height + TOOLTIP_GAP;
          left = sr.x + sr.width / 2 - tooltipWidth / 2;
          break;
        case 'top':
          top = sr.y - tooltipEstHeight - TOOLTIP_GAP;
          left = sr.x + sr.width / 2 - tooltipWidth / 2;
          break;
        case 'right':
          top = sr.y + sr.height / 2 - tooltipEstHeight / 2;
          left = sr.x + sr.width + TOOLTIP_GAP;
          break;
        case 'left':
          top = sr.y + sr.height / 2 - tooltipEstHeight / 2;
          left = sr.x - tooltipWidth - TOOLTIP_GAP;
          break;
      }

      if (left < 12) left = 12;
      if (left + tooltipWidth > vw - 12) left = vw - tooltipWidth - 12;
      if (top < 12) top = 12;
      if (top + tooltipEstHeight > vh - 12) top = vh - tooltipEstHeight - 12;

      setTooltipStyle({ top, left });
      setVisible(true);
    };

    const tryFind = () => {
      const el = document.querySelector(step.target);
      if (!el) {
        attempt++;
        if (attempt < maxAttempts) {
          timerId = setTimeout(tryFind, delays[attempt]);
          return;
        }
        // Element not found after all retries — skip to next step
        next();
        return;
      }

      // Scroll element into view, then measure after scroll settles
      el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
      setTimeout(() => positionSpotlight(el), 350);
    };

    let timerId = setTimeout(tryFind, delays[0]);

    return () => clearTimeout(timerId);
  }, [isActive, step, currentStep]);

  useEffect(() => {
    updateSpotlight();
    window.addEventListener('resize', updateSpotlight);
    return () => window.removeEventListener('resize', updateSpotlight);
  }, [updateSpotlight]);

  // Keyboard navigation
  useEffect(() => {
    if (!isActive) return;

    const handleKey = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowRight':
        case 'Enter':
          e.preventDefault();
          next();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          prev();
          break;
        case 'Escape':
          e.preventDefault();
          finish();
          break;
      }
    };

    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isActive, next, prev, finish]);

  // Body scroll lock
  useEffect(() => {
    if (isActive) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isActive]);

  if (!isActive || !step) return null;

  return (
    <div
      className="tour-overlay"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 10000,
        animation: 'tourOverlayFadeIn 0.3s ease-out',
      }}
    >
      {/* SVG mask spotlight */}
      <svg
        style={{ position: 'fixed', inset: 0, width: '100%', height: '100%', zIndex: 10000 }}
        onClick={finish}
      >
        <defs>
          <mask id="tour-spotlight-mask">
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            {spotlight && (
              <rect
                x={spotlight.x}
                y={spotlight.y}
                width={spotlight.width}
                height={spotlight.height}
                rx="8"
                ry="8"
                fill="black"
              />
            )}
          </mask>
        </defs>
        <rect
          x="0" y="0" width="100%" height="100%"
          fill="rgba(0, 0, 0, 0.6)"
          mask="url(#tour-spotlight-mask)"
        />
      </svg>

      {/* Pulse ring around spotlight */}
      {spotlight && (
        <div
          style={{
            position: 'fixed',
            left: spotlight.x - 4,
            top: spotlight.y - 4,
            width: spotlight.width + 8,
            height: spotlight.height + 8,
            borderRadius: 12,
            zIndex: 10001,
            animation: 'tourPulse 2s ease-in-out infinite',
            border: '2px solid rgba(229, 39, 19, 0.4)',
            pointerEvents: 'none',
          }}
        />
      )}

      {/* Tooltip */}
      {visible && (
        <TourTooltip
          style={tooltipStyle}
          placement={step.placement}
          title={step.title}
          description={step.description}
        />
      )}
    </div>
  );
}
