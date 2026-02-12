import { Clock, Loader2 } from "lucide-react";
import { Session, GenerationStatus } from "@/types";
import { SESSION_TYPE_CONFIG } from "@/config/session-display";

interface SessionThumbnailProps {
  session: Session;
  onClick?: () => void;
  size?: "sm" | "md" | "lg";
}

export function SessionThumbnail({ session, onClick, size = "md" }: SessionThumbnailProps) {
  const config = SESSION_TYPE_CONFIG[session.session_type];
  const sizeClasses = {
    sm: "p-2.5",
    md: "p-3",
    lg: "p-4",
  };
  
  const isGenerating = session.generation_status === GenerationStatus.IN_PROGRESS;
  const isPending = session.generation_status === GenerationStatus.PENDING;
  const isGenerated = session.generation_status === GenerationStatus.COMPLETED;

  return (
    <button
      onClick={onClick}
      disabled={isPending || isGenerating}
      className={`${sizeClasses[size]} rounded-xl bg-background-card hover:bg-background-secondary transition-all duration-200 active:scale-[0.98] group ${isPending ? 'opacity-70' : ''}`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${config.color}`}>
          <span className="text-lg">{config.icon}</span>
        </div>
        <div className="flex items-center gap-2">
          {isGenerating && (
            <div className="flex items-center gap-1 text-xs text-primary">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Generating</span>
            </div>
          )}
          {session.estimated_duration_minutes && isGenerated && (
            <div className="flex items-center gap-1 text-xs text-foreground-muted">
              <Clock className="w-3 h-3" />
              {session.estimated_duration_minutes}m
            </div>
          )}
        </div>
      </div>

      <div className="text-sm font-semibold text-foreground mb-1">
        Day {session.day_number}
      </div>

      <div className="text-xs font-medium text-primary mb-2">
        {config.label}
      </div>

      {/* Show skeleton loading state for pending/in-progress sessions */}
      {(isPending || isGenerating) ? (
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-foreground-muted">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
            <span>Warmup...</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-foreground-muted">
            <div className="w-1.5 h-1.5 rounded-full bg-primary" />
            <span>Main exercises...</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-foreground-muted">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
            <span>Accessory...</span>
          </div>
        </div>
      ) : (
        <div className="space-y-1">
          {session.warmup && session.warmup.length > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-foreground-muted">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
              <span>Warmup ({session.warmup.length} exercises)</span>
            </div>
          )}

          {session.main && session.main.length > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-foreground-muted">
              <div className="w-1.5 h-1.5 rounded-full bg-primary" />
              <span>Main ({session.main.length} exercises)</span>
            </div>
          )}

          {session.accessory && session.accessory.length > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-foreground-muted">
              <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
              <span>Accessory ({session.accessory.length} exercises)</span>
            </div>
          )}

          {session.finisher && (
            <div className="flex items-center gap-1.5 text-xs text-foreground-muted">
              <div className="w-1.5 h-1.5 rounded-full bg-orange-400" />
              <span>Finisher ({session.finisher.type}{session.finisher.exercises ? ` (${session.finisher.exercises.length} exercises)` : ''})</span>
            </div>
          )}

          {session.cooldown && session.cooldown.length > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-foreground-muted">
              <div className="w-1.5 h-1.5 rounded-full bg-teal-400" />
              <span>Cooldown ({session.cooldown.length} exercises)</span>
            </div>
          )}
        </div>
      )}

      {session.intent_tags && session.intent_tags.length > 0 && (
        <div className="mt-2 pt-2 border-t border-border flex flex-wrap gap-1">
          {session.intent_tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="text-xs px-2 py-0.5 rounded-full bg-background-elevated text-foreground-muted"
            >
              {tag}
            </span>
          ))}
          {session.intent_tags.length > 3 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-background-elevated text-foreground-muted">
              +{session.intent_tags.length - 3}
            </span>
          )}
        </div>
      )}
    </button>
  );
}
