import { Calendar, Clock, TrendingUp, Activity } from "lucide-react";
import { MicrocycleWithSessions } from "@/types";

interface ProgramStatsProps {
  microcycles: MicrocycleWithSessions[];
}

export function ProgramStats({ microcycles }: ProgramStatsProps) {
  const totalSessions = microcycles.reduce((sum, mc) => sum + mc.sessions.length, 0);
  const totalDuration = microcycles.reduce((sum, mc) => {
    return sum + mc.sessions.reduce((sSum, s) => sSum + (s.estimated_duration_minutes || 0), 0);
  }, 0);
  const activeMicrocycle = microcycles.find((mc) => mc.status === "active");
  const completedMicrocycles = microcycles.filter((mc) => mc.status === "complete").length;
  const plannedMicrocycles = microcycles.filter((mc) => mc.status === "planned").length;

  const avgSessionDuration = totalSessions > 0 ? Math.round(totalDuration / totalSessions) : 0;
  const weeksRemaining = plannedMicrocycles;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div className="rounded-xl bg-background-card p-4">
        <div className="flex items-center gap-2 mb-2">
          <Activity className="w-5 h-5 text-primary" />
          <span className="text-sm font-medium text-foreground-muted">Total Sessions</span>
        </div>
        <div className="text-2xl font-bold text-foreground">{totalSessions}</div>
      </div>

      <div className="rounded-xl bg-background-card p-4">
        <div className="flex items-center gap-2 mb-2">
          <Clock className="w-5 h-5 text-primary" />
          <span className="text-sm font-medium text-foreground-muted">Total Time</span>
        </div>
        <div className="text-2xl font-bold text-foreground">{totalDuration}m</div>
        <div className="text-xs text-foreground-muted mt-1">
          Avg {avgSessionDuration}m per session
        </div>
      </div>

      <div className="rounded-xl bg-background-card p-4">
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="w-5 h-5 text-primary" />
          <span className="text-sm font-medium text-foreground-muted">Progress</span>
        </div>
        <div className="text-2xl font-bold text-foreground">
          {completedMicrocycles}/{microcycles.length}
        </div>
        <div className="text-xs text-foreground-muted mt-1">microcycles completed</div>
      </div>

      <div className="rounded-xl bg-background-card p-4">
        <div className="flex items-center gap-2 mb-2">
          <Calendar className="w-5 h-5 text-primary" />
          <span className="text-sm font-medium text-foreground-muted">Weeks Left</span>
        </div>
        <div className="text-2xl font-bold text-foreground">{weeksRemaining}</div>
        {activeMicrocycle && (
          <div className="text-xs text-foreground-muted mt-1">
            Week {activeMicrocycle.sequence_number} active
          </div>
        )}
      </div>
    </div>
  );
}
