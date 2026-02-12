import { Calendar, Target, TrendingUp, ChevronRight } from "lucide-react";
import { Program } from "@/types";

interface ProgramCardProps {
  program: Program;
  onClick?: () => void;
}

export function ProgramCard({ program, onClick }: ProgramCardProps) {
  const goals = [program.goal_1, program.goal_2, program.goal_3].filter(Boolean);
  const goalLabels = goals.map((goal) =>
    goal.replace("_", " ").replace(/\b\w/g, (word) =>
      word.charAt(0).toUpperCase() + word.slice(1).toLowerCase(),
    ),
  );

  return (
    <button
      onClick={onClick}
      className="w-full text-left rounded-xl bg-background-card p-[var(--padding-card-md)] hover:bg-background-secondary transition-all duration-200 active:scale-[0.98] group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-background focus-visible:ring-primary"
    >
      <div className="flex items-start justify-between mb-[var(--spacing-lg)]">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-foreground group-hover:text-primary transition-colors">
            {program.name || "Untitled Program"}
          </h3>
          {program.program_start_date && (
            <p className="text-sm text-foreground-muted mt-1 flex items-center gap-[var(--spacing-sm)]">
              <Calendar className="w-3.5 h-3.5" />
              <span>
                {new Date(program.program_start_date).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </span>
            </p>
          )}
        </div>
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
            program.is_active
              ? "bg-primary text-background"
              : "bg-background-elevated text-foreground-muted"
          }`}
        >
          {program.is_active ? (
            <div className="w-2 h-2 rounded-full bg-background" />
          ) : (
            <div className="w-2 h-2 rounded-full bg-foreground-muted/30" />
          )}
        </div>
      </div>

      {goals.length > 0 && (
        <div className="flex flex-wrap gap-[var(--spacing-sm)] mb-[var(--spacing-lg)]">
          {goalLabels.map((goal) => (
            <span
              key={goal}
              className="flex items-center gap-[var(--spacing-xs)] px-[var(--spacing-sm)] py-[var(--spacing-xs)] rounded-full bg-background-elevated text-xs font-medium text-foreground"
            >
              <Target className="w-3 h-3 text-primary" />
              {goal}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center gap-[var(--spacing-xl)] text-sm">
        <div className="flex items-center gap-[var(--spacing-sm)] text-foreground-muted">
          <TrendingUp className="w-4 h-4" />
          <span>{program.duration_weeks} weeks</span>
        </div>
        <div className="flex items-center gap-1.5 text-foreground-muted">
          <Target className="w-4 h-4" />
          <span>{program.days_per_week} days/week</span>
        </div>
      </div>

      <div className="flex items-center justify-center mt-[var(--spacing-lg)] text-primary">
        <ChevronRight className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" />
      </div>
    </button>
  );
}
