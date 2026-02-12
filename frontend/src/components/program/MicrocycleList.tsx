import { ChevronDown, ChevronRight, Calendar, Clock, Loader2 } from "lucide-react";
import { useState } from "react";
import { MicrocycleWithSessions, MicrocycleStatus, GenerationStatus } from "@/types";
import { GENERATION_STATUS_CONFIG } from "@/config/session-display";

interface MicrocycleListProps {
  microcycles: MicrocycleWithSessions[];
  onMicrocycleClick?: (microcycleId: number) => void;
}

const STATUS_CONFIG: Record<MicrocycleStatus, { label: string; color: string; bg: string }> = {
  planned: { label: "Planned", color: "text-blue-400", bg: "bg-blue-500/10" },
  active: { label: "Active", color: "text-primary", bg: "bg-primary/10" },
  complete: { label: "Complete", color: "text-success", bg: "bg-success/10" },
};

export function MicrocycleList({ microcycles, onMicrocycleClick }: MicrocycleListProps) {
  const [expandedMicrocycleId, setExpandedMicrocycleId] = useState<number | null>(null);

  return (
    <div className="space-y-3">
      {microcycles.map((microcycle) => {
        const statusConfig = STATUS_CONFIG[microcycle.status];
        const isExpanded = expandedMicrocycleId === microcycle.id;
        
        const generationStatus = microcycle.generation_status || GenerationStatus.PENDING;
        const generationConfig = GENERATION_STATUS_CONFIG[generationStatus];
        const isGenerating = generationStatus === GenerationStatus.IN_PROGRESS;
        const isGenerated = generationStatus === GenerationStatus.COMPLETED;

        const totalDuration = microcycle.sessions.reduce((sum, session) => {
          return sum + (session.estimated_duration_minutes || 0);
        }, 0);

        const sessionsWithGeneration = microcycle.sessions.map(session => ({
          ...session,
          generation_status: session.generation_status || GenerationStatus.PENDING,
        }));
        const completedSessions = sessionsWithGeneration.filter(
          s => s.generation_status === GenerationStatus.COMPLETED
        ).length;

        return (
          <div key={microcycle.id} className="rounded-xl bg-background-card overflow-hidden">
            <button
              onClick={() => {
                setExpandedMicrocycleId(isExpanded ? null : microcycle.id);
                onMicrocycleClick?.(microcycle.id);
              }}
              className="w-full px-4 py-3 flex items-start justify-between hover:bg-background-secondary transition-colors"
            >
              <div className="flex items-start gap-3 flex-1">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center ${statusConfig.bg} ${statusConfig.color} shrink-0`}
                >
                  <Calendar className="w-4 h-4" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-foreground">
                      Microcycle {microcycle.sequence_number}
                    </h3>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${statusConfig.bg} ${statusConfig.color}`}>
                      {statusConfig.label}
                    </span>
                    {microcycle.is_deload && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-warning/10 text-warning">
                        Deload
                      </span>
                    )}
                    <span className={`text-xs px-2 py-0.5 rounded-full ${generationConfig.bg} ${generationConfig.color}`}>
                      {isGenerating ? (
                        <span className="flex items-center gap-1">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          {generationConfig.label}
                        </span>
                      ) : (
                        generationConfig.label
                      )}
                    </span>
                  </div>
                  {microcycle.micro_start_date && (
                    <p className="text-sm text-foreground-muted mt-0.5 flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {new Date(microcycle.micro_start_date).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                      })}
                      {" "}
                      · {microcycle.length_days} days
                    </p>
                  )}
                  {isGenerating && (
                    <p className="text-xs text-primary mt-1">
                      {completedSessions} of {microcycle.sessions.length} sessions generated
                    </p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <div className="text-right">
                  <div className="text-sm text-foreground-muted flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {isGenerated ? `${totalDuration}m` : '...'}
                  </div>
                  <div className="text-xs text-foreground-muted">
                    {microcycle.sessions.length} sessions
                  </div>
                </div>
                {isExpanded ? (
                  <ChevronDown className="w-5 h-5 text-foreground-muted" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-foreground-muted" />
                )}
              </div>
            </button>

            {isExpanded && (
              <div className="px-4 py-3 border-t border-border bg-background-elevated">
                <div className="space-y-2">
                  {microcycle.sessions.map((session) => {
                    const sessionGenStatus = session.generation_status || GenerationStatus.PENDING;
                    const isSessionGenerating = sessionGenStatus === GenerationStatus.IN_PROGRESS;
                    const isSessionPending = sessionGenStatus === GenerationStatus.PENDING;
                    
                    return (
                      <div
                        key={session.id}
                        className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors cursor-pointer ${
                          isSessionPending || isSessionGenerating
                            ? 'bg-background-secondary opacity-70'
                            : 'bg-background hover:bg-background-secondary'
                        }`}
                      >
                        <div className="text-xs text-foreground-muted w-16 shrink-0">
                          Day {session.day_number}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <div className="text-sm font-medium text-foreground">
                              {session.session_type.replace("_", " ").replace(/\b\w/g, (word) =>
                                word.charAt(0).toUpperCase() + word.slice(1).toLowerCase(),
                              )}
                            </div>
                            {isSessionGenerating && (
                              <span className="text-xs text-primary flex items-center gap-1">
                                <Loader2 className="w-3 h-3 animate-spin" />
                                Generating
                              </span>
                            )}
                            {isSessionPending && (
                              <span className="text-xs text-gray-400">
                                Pending
                              </span>
                            )}
                          </div>
                          {session.estimated_duration_minutes && isGenerated && (
                            <div className="text-xs text-foreground-muted flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {session.estimated_duration_minutes}m
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
