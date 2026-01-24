import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIState {
  // Menu state
  isMenuOpen: boolean;
  setMenuOpen: (open: boolean) => void;
  toggleMenu: () => void;
  
  // Active program (for dashboard context)
  activeProgramId: number | null;
  setActiveProgramId: (id: number | null) => void;
  
  // Active workout session
  activeWorkoutSessionId: number | null;
  setActiveWorkoutSessionId: (id: number | null) => void;
  
  // Program wizard step (for multi-step form)
  programWizardStep: number;
  setProgramWizardStep: (step: number) => void;
  nextWizardStep: () => void;
  prevWizardStep: () => void;
  resetWizardStep: () => void;
  
  // Toast notifications
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  
  // Theme (for future light mode support)
  theme: 'dark' | 'light';
  setTheme: (theme: 'dark' | 'light') => void;
}

interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}

let toastId = 0;

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      // Menu state
      isMenuOpen: false,
      setMenuOpen: (open) => set({ isMenuOpen: open }),
      toggleMenu: () => set((state) => ({ isMenuOpen: !state.isMenuOpen })),
      
      // Active program
      activeProgramId: null,
      setActiveProgramId: (id) => set({ activeProgramId: id }),
      
      // Active workout
      activeWorkoutSessionId: null,
      setActiveWorkoutSessionId: (id) => set({ activeWorkoutSessionId: id }),
      
      // Program wizard
      programWizardStep: 1,
      setProgramWizardStep: (step) => set({ programWizardStep: step }),
      nextWizardStep: () => set((state) => ({ programWizardStep: state.programWizardStep + 1 })),
      prevWizardStep: () => set((state) => ({ programWizardStep: Math.max(1, state.programWizardStep - 1) })),
      resetWizardStep: () => set({ programWizardStep: 1 }),
      
      // Toasts
      toasts: [],
      addToast: (toast) => {
        const id = `toast-${++toastId}`;
        set((state) => ({
          toasts: [...state.toasts, { ...toast, id }],
        }));
        
        // Auto-remove after duration
        if (toast.duration !== 0) {
          setTimeout(() => {
            set((state) => ({
              toasts: state.toasts.filter((t) => t.id !== id),
            }));
          }, toast.duration || 3000);
        }
      },
      removeToast: (id) => set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      })),
      
      // Theme
      theme: 'dark',
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'gainsly-ui-storage',
      partialize: (state) => ({
        activeProgramId: state.activeProgramId,
        theme: state.theme,
      }),
    }
  )
);
