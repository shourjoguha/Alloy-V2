import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { useUIStore } from '@/stores/ui-store';
import { cn } from '@/lib/utils';

const icons = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const styles = {
  success: 'bg-success text-white',
  error: 'bg-error text-white',
  warning: 'bg-warning text-white',
  info: 'bg-primary text-white',
};

export function ToastContainer() {
  const { toasts, removeToast } = useUIStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-20 left-0 right-0 z-50 safe-bottom pointer-events-none">
      <div className="container-app flex flex-col gap-2">
        {toasts.map((toast) => {
          const Icon = icons[toast.type];
          
          return (
            <div
              key={toast.id}
              className={cn(
                'pointer-events-auto flex items-center gap-3 rounded-lg border p-4 animate-slide-up',
                styles[toast.type]
              )}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              <span className="flex-1 text-sm font-medium text-foreground">
                {toast.message}
              </span>
              <button
                onClick={() => removeToast(toast.id)}
                className="flex-shrink-0 rounded p-1 hover:bg-white/20 transition-colors"
                aria-label="Dismiss"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
