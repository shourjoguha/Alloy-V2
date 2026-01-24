import { useProgramWizardStore } from '@/stores/program-wizard-store';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

const DURATION_OPTIONS = [30, 45, 60, 75, 90, 120];

export function SplitStep() {
  const { daysPerWeek, setDaysPerWeek, maxDuration, setMaxDuration } = useProgramWizardStore();

  return (
    <div className="space-y-8">
      <div className="text-center space-y-2">
        <h2 className="text-xl font-bold">Training Schedule</h2>
        <p className="text-foreground-muted text-sm">
          How much time can you dedicate to training?
        </p>
      </div>

      {/* Days per week selector */}
      <div className="space-y-3">
        <label className="text-sm font-medium">Days per week</label>
        <div className="grid grid-cols-6 gap-2">
          {[2, 3, 4, 5, 6, 7].map((days) => (
            <button
              key={days}
              onClick={() => setDaysPerWeek(days)}
              className={cn(
                "h-12 rounded-lg font-bold transition-all",
                daysPerWeek === days
                  ? "bg-primary text-white"
                  : "bg-background-input hover:bg-background-secondary text-foreground"
              )}
            >
              {days}
            </button>
          ))}
        </div>
        <p className="text-xs text-foreground-muted text-center">
          {daysPerWeek <= 3 && "Great for recovery and consistency"}
          {daysPerWeek === 4 && "Sweet spot for most lifters"}
          {daysPerWeek === 5 && "Good volume and frequency balance"}
          {daysPerWeek >= 6 && "High frequency - ensure adequate recovery"}
        </p>
      </div>

      {/* Max Duration selector */}
      <div className="space-y-3">
        <label className="text-sm font-medium">Max Minutes per Session</label>
        <div className="grid grid-cols-3 gap-3">
          {DURATION_OPTIONS.map((mins) => (
            <button
              key={mins}
              onClick={() => setMaxDuration(mins)}
              className={cn(
                "h-14 rounded-lg font-medium transition-all flex flex-col items-center justify-center gap-1",
                maxDuration === mins
                  ? "bg-primary text-white"
                  : "bg-background-input hover:bg-background-secondary text-foreground"
              )}
            >
              <span className="text-lg font-bold">{mins}</span>
              <span className="text-[10px] opacity-80">MINUTES</span>
            </button>
          ))}
        </div>
      </div>

      {/* Summary hint */}
      <Card variant="grouped" className="p-4 text-center">
        <p className="text-sm text-foreground-muted">
          <span className="text-cta">✓ Jerome will design a program for {daysPerWeek} days/week, max {maxDuration} mins/day.</span>
        </p>
      </Card>
    </div>
  );
}
