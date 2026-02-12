import { Calendar, Target, TrendingUp, type LucideIcon } from "lucide-react";

import { Program, Goal } from "@/types";

const GOAL_ICONS: Record<Goal, { icon: LucideIcon; label: string }> = {
  strength: { icon: Target, label: "Strength" },
  hypertrophy: { icon: TrendingUp, label: "Hypertrophy" },
  endurance: { icon: TrendingUp, label: "Endurance" },
  fat_loss: { icon: Target, label: "Fat Loss" },
  mobility: { icon: Target, label: "Mobility" },
  explosiveness: { icon: Target, label: "Explosiveness" },
  speed: { icon: TrendingUp, label: "Speed" },
};

interface ProgramHeaderProps {
  program: Program;
}

export function ProgramHeader({ program }: ProgramHeaderProps) {
  const goals = [program.goal_1, program.goal_2, program.goal_3].filter(Boolean) as Goal[];
  const goalsWithWeights = goals.map((goal) => ({
    goal,
    weight: program[`goal_weight_${1 + goals.indexOf(goal)}` as "goal_weight_1" | "goal_weight_2" | "goal_weight_3"],
  }));

  return (
    <div className="mb-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground leading-tight">
            {program.name || "Untitled Program"}
          </h1>
          {program.program_start_date && (
            <p className="text-sm font-normal text-foreground-muted mt-2 flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              <span>
                {new Date(program.program_start_date).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </span>
              {program.duration_weeks && (
                <>
                  {" "}
                  · {program.duration_weeks} weeks
                </>
              )}
            </p>
          )}
        </div>
        <div
          className={`px-3 py-1 rounded-full text-xs font-medium ${
            program.is_active
              ? "bg-primary text-background"
              : "bg-background-elevated text-foreground-muted"
          }`}
        >
          {program.is_active ? "Active" : "Inactive"}
        </div>
      </div>

      {goalsWithWeights.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3">
          {goalsWithWeights.map(({ goal, weight }) => {
            const config = GOAL_ICONS[goal];
            if (!config) return null;

            const Icon = config.icon;
            return (
              <div
                key={goal}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-background-elevated"
              >
                <Icon className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium text-foreground">
                  {config.label}
                </span>
                <span className="text-xs text-foreground-muted">({weight})</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
