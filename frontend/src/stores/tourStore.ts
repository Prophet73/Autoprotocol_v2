import { create } from 'zustand';
import { tourSteps, type TourStep } from '../components/tour/tourSteps';

interface TourState {
  isActive: boolean;
  currentStep: number;
  activeSteps: TourStep[];
  start: (isAdmin: boolean, hasAnalytics: boolean) => void;
  next: () => void;
  prev: () => void;
  finish: () => void;
}

export const useTourStore = create<TourState>((set, get) => ({
  isActive: false,
  currentStep: 0,
  activeSteps: [],

  start: (isAdmin: boolean, hasAnalytics: boolean) => {
    const filtered = tourSteps.filter((step) => {
      if (step.adminOnly && !isAdmin) return false;
      if (step.viewerOnly && !hasAnalytics) return false;
      return true;
    });
    set({ isActive: true, currentStep: 0, activeSteps: filtered });
  },

  next: () => {
    const { currentStep, activeSteps } = get();
    if (currentStep < activeSteps.length - 1) {
      set({ currentStep: currentStep + 1 });
    } else {
      get().finish();
    }
  },

  prev: () => {
    const { currentStep } = get();
    if (currentStep > 0) {
      set({ currentStep: currentStep - 1 });
    }
  },

  finish: () => {
    set({ isActive: false, currentStep: 0, activeSteps: [] });
  },
}));
